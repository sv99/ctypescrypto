"""
Implements interface to openssl X509 and X509Store structures, 
I.e allows to load, analyze and verify certificates.

X509Store objects are also used to verify other signed documets,
such as CMS, OCSP and timestamps.
"""



from ctypes import c_void_p,create_string_buffer,c_long,c_int,POINTER,c_char_p,Structure,cast
from ctypescrypto.bio import Membio
from ctypescrypto.pkey import PKey
from ctypescrypto.oid import Oid
from ctypescrypto.exception import LibCryptoError
from ctypescrypto import libcrypto
from datetime import datetime
try:
	from pytz import utc
except ImportError:
	from datetime import timedelta,tzinfo
	ZERO=timedelta(0)
	class UTC(tzinfo):
		"""tzinfo object for UTC. 
			If no pytz is available, we would use it.
		"""

		def utcoffset(self, dt):
			return ZERO

		def tzname(self, dt):
			return "UTC"

		def dst(self, dt):
			return ZERO

	utc=UTC()

__all__ = ['X509','X509Error','X509Name','X509Store','StackOfX509']

class _validity(Structure):
	""" ctypes representation of X509_VAL structure 
		needed to access certificate validity period, because openssl
		doesn't provide fuctions for it - only macros
	"""
	_fields_ = 	[('notBefore',c_void_p),('notAfter',c_void_p)]

class _cinf(Structure):
	""" ctypes representtion of X509_CINF structure 
	    neede to access certificate data, which are accessable only
		via macros
	"""
	_fields_ = [('version',c_void_p),
		('serialNumber',c_void_p),
		('sign_alg',c_void_p),
		('issuer',c_void_p),
		('validity',POINTER(_validity)),
		('subject',c_void_p),
		('pubkey',c_void_p),
		('issuerUID',c_void_p),
		('subjectUID',c_void_p),
		('extensions',c_void_p),
		]

class _x509(Structure):
	"""
	ctypes represntation of X509 structure needed
	to access certificate data which are accesable only via
	macros, not functions
	"""
	_fields_ = [('cert_info',POINTER(_cinf)),
				('sig_alg',c_void_p),
				('signature',c_void_p),
				# There are a lot of parsed extension fields there
				]
_px509 = POINTER(_x509)

class X509Error(LibCryptoError):
	"""
	Exception, generated when some openssl function fail
	during X509 operation
	"""
	pass


class X509Name(object):
	"""
	Class which represents X.509 distinguished name - typically 
	a certificate subject name or an issuer name.

	Now used only to represent information, extracted from the
	certificate. Potentially can be also used to build DN when creating
	certificate signing request
	"""
	# XN_FLAG_SEP_COMMA_PLUS & ASN1_STRFLG_UTF8_CONVERT
	PRINT_FLAG=0x10010
	ESC_MSB=4
	def __init__(self,ptr=None,copy=False):
		"""
		Creates a X509Name object
		@param ptr - pointer to X509_NAME C structure (as returned by some  OpenSSL functions
		@param copy - indicates that this structure have to be freed upon object destruction
		"""
		if ptr is not None:
			self.ptr=ptr
			self.need_free=copy
			self.writable=False
		else:
			self.ptr=libcrypto.X509_NAME_new()
			self.need_free=True
			self.writable=True
	def __del__(self):
		"""
		Frees if neccessary
		"""
		if self.need_free:
			libcrypto.X509_NAME_free(self.ptr)
	def __str__(self):
		"""
		Produces an ascii representation of the name, escaping all symbols > 0x80
		Probably it is not what you want, unless your native language is English
		"""
		b=Membio()
		libcrypto.X509_NAME_print_ex(b.bio,self.ptr,0,self.PRINT_FLAG | self.ESC_MSB)
		return str(b)
	def __unicode__(self):
		"""
		Produces unicode representation of the name. 
		"""
		b=Membio()
		libcrypto.X509_NAME_print_ex(b.bio,self.ptr,0,self.PRINT_FLAG)
		return unicode(b)
	def __len__(self):
		"""
		return number of components in the name
		"""
		return libcrypto.X509_NAME_entry_count(self.ptr)
	def __cmp__(self,other):
		"""
		Compares X509 names
		"""
		return libcrypto.X509_NAME_cmp(self.ptr,other.ptr)
	def __eq__(self,other):
		return libcrypto.X509_NAME_cmp(self.ptr,other.ptr)==0

	def __getitem__(self,key):
		if isinstance(key,Oid):
			# Return first matching field
			idx=libcrypto.X509_NAME_get_index_by_NID(self.ptr,key.nid,-1)
			if idx<0:
				raise KeyError("Key not found "+str(Oid))
			entry=libcrypto.X509_NAME_get_entry(self.ptr,idx)
			s=libcrypto.X509_NAME_ENTRY_get_data(entry)
			b=Membio()
			libcrypto.ASN1_STRING_print_ex(b.bio,s,self.PRINT_FLAG)
			return unicode(b)
		elif isinstance(key,(int,long)):
			# Return OID, string tuple
			entry=libcrypto.X509_NAME_get_entry(self.ptr,key)
			if entry is None:
				raise IndexError("name entry index out of range")
			oid=Oid.fromobj(libcrypto.X509_NAME_ENTRY_get_object(entry))
			s=libcrypto.X509_NAME_ENTRY_get_data(entry)
			b=Membio()
			libcrypto.ASN1_STRING_print_ex(b.bio,s,self.PRINT_FLAG)
			return (oid,unicode(b))
		else:
			raise TypeError("X509 NAME can be indexed by Oids or integers only")

	def __setitem__(self,key,val):
		if not self.writable:
			raise ValueError("Attempt to modify constant X509 object")
		else:
			raise NotImplementedError
	def __delitem__(self,key):
		if not self.writable:
			raise ValueError("Attempt to modify constant X509 object")
		else:
			raise NotImplementedError
	def __hash__(self):
		return libcrypto.X509_NAME_hash(self.ptr)

class _x509_ext(Structure):
	""" Represens C structure X509_EXTENSION """
	_fields_=[("object",c_void_p),
			("critical",c_int),
			("value",c_void_p)]

class X509_EXT(object):
	""" Python object which represents a certificate extension """
	def __init__(self,ptr,copy=False):
		""" Initializes from the pointer to X509_EXTENSION.
			If copy is True, creates a copy, otherwise just
			stores pointer.
		"""
		if copy:
			self.ptr=libcrypto.X509_EXTENSION_dup(ptr)
		else:
			self.ptr=cast(ptr,POINTER(_x509_ext))
	def __del__(self):
		libcrypto.X509_EXTENSION_free(self.ptr)
	def __str__(self):
		b=Membio()
		libcrypto.X509V3_EXT_print(b.bio,self.ptr,0x20010,0)
		return str(b)
	def __unicode__(self):
		b=Membio()
		libcrypto.X509V3_EXT_print(b.bio,self.ptr,0x20010,0)
		return unicode(b)
	@property
	def oid(self):
		return Oid.fromobj(self.ptr[0].object)
	@property
	def critical(self):	
		return self.ptr[0].critical >0
class _X509extlist(object):	
	"""
	Represents list of certificate extensions
	"""
	def __init__(self,cert):
		self.cert=cert
	def __len__(self):
		return libcrypto.X509_get_ext_count(self.cert.cert)
	def __getitem__(self,item):
		p=libcrypto.X509_get_ext(self.cert.cert,item)
		if p is None:
			raise IndexError
		return X509_EXT(p,True)
	def find(self,oid):
		"""
		Return list of extensions with given Oid
		"""
		if not isinstance(oid,Oid):
			raise TypeError("Need crytypescrypto.oid.Oid as argument")
		found=[]
		l=-1
		end=len(self)
		while True:
			l=libcrypto.X509_get_ext_by_NID(self.cert.cert,oid.nid,l)
			if l>=end or l<0:
				 break
			found.append(self[l])
		return found
	def find_critical(self,crit=True):
		"""
		Return list of critical extensions (or list of non-cricital, if
		optional second argument is False
		"""
		if crit:
			flag=1
		else:
			flag=0
		found=[]
		end=len(self)
		l=-1
		while True:
			l=libcrypto.X509_get_ext_by_critical(self.cert.cert,flag,l)
			if l>=end or l<0:
				 break
			found.append(self[l])
		return found			

class X509(object):
	"""
	Represents X.509 certificate. 
	"""
	def __init__(self,data=None,ptr=None,format="PEM"):
		"""
		Initializes certificate
		@param data - serialized certificate in PEM or DER format.
		@param ptr - pointer to X509, returned by some openssl function. 
			mutually exclusive with data
		@param format - specifies data format. "PEM" or "DER", default PEM
		"""
		if ptr is not None:
			if data is not None: 
				raise TypeError("Cannot use data and ptr simultaneously")
			self.cert = ptr
		elif data is None:
			raise TypeError("data argument is required")
		else:
			b=Membio(data)
			if format == "PEM":
				self.cert=libcrypto.PEM_read_bio_X509(b.bio,None,None,None)
			else:
				self.cert=libcrypto.d2i_X509_bio(b.bio,None)
			if self.cert is None:
				raise X509Error("error reading certificate")
		self.extensions=_X509extlist(self)		
	def __del__(self):
		"""
		Frees certificate object
		"""
		libcrypto.X509_free(self.cert)
	def __str__(self):
		""" Returns der string of the certificate """
		b=Membio()
		if libcrypto.i2d_X509_bio(b.bio,self.cert)==0:
			raise X509Error("error serializing certificate")
		return str(b)
	def __repr__(self):
		""" Returns valid call to the constructor """
		return "X509(data="+repr(str(self))+",format='DER')"
	@property
	def pubkey(self):
		"""EVP PKEy object of certificate public key"""
		return PKey(ptr=libcrypto.X509_get_pubkey(self.cert,False))
	def pem(self):
		""" Returns PEM represntation of the certificate """
		b=Membio()
		if libcrypto.PEM_write_bio_X509(b.bio,self.cert)==0:
			raise X509Error("error serializing certificate")
		return str(b)
	def verify(self,store=None,chain=[],key=None):	
		""" 
		Verify self. Supports verification on both X509 store object 
		or just public issuer key
		@param store X509Store object.
		@param chain - list of X509 objects to add into verification
			context.These objects are untrusted, but can be used to
			build certificate chain up to trusted object in the store
		@param key - PKey object with open key to validate signature
		
		parameters store and key are mutually exclusive. If neither 
		is specified, attempts to verify self as self-signed certificate
		"""
		if store is not None and key is not None:
			raise X509Error("key and store cannot be specified simultaneously")
		if store is not None:
			ctx=libcrypto.X509_STORE_CTX_new()
			if ctx is None:
				raise X509Error("Error allocating X509_STORE_CTX")
			if chain is not None and len(chain)>0:
				ch=StackOfX509(chain)
			else:
				ch=None
			if libcrypto.X509_STORE_CTX_init(ctx,store.store,self.cert,ch) < 0:
				raise X509Error("Error allocating X509_STORE_CTX")
			res= libcrypto.X509_verify_cert(ctx)
			libcrypto.X509_STORE_CTX_free(ctx)
			return res>0
		else:
			if key is None:
				if self.issuer != self.subject:
					# Not a self-signed certificate
					return False
				key = self.pubkey
			res = libcrypto.X509_verify(self.cert,key.key)
			if res < 0:
				raise X509Error("X509_verify failed")
			return res>0
			
	@property
	def subject(self):
		""" X509Name for certificate subject name """
		return X509Name(libcrypto.X509_get_subject_name(self.cert))
	@property
	def issuer(self):
		""" X509Name for certificate issuer name """
		return X509Name(libcrypto.X509_get_issuer_name(self.cert))
	@property
	def serial(self):
		""" Serial number of certificate as integer """
		asnint=libcrypto.X509_get_serialNumber(self.cert)
		b=Membio()
		libcrypto.i2a_ASN1_INTEGER(b.bio,asnint)
		return int(str(b),16)
	@property 
	def version(self):
		""" certificate version as integer. Really certificate stores 0 for
		version 1 and 2 for version 3, but we return 1 and 3 """
		asn1int=cast(self.cert,_px509)[0].cert_info[0].version
		return libcrypto.ASN1_INTEGER_get(asn1int)+1
	@property
	def startDate(self):
		""" Certificate validity period start date """
		# Need deep poke into certificate structure (x)->cert_info->validity->notBefore	
		global utc
		asn1date=cast(self.cert,_px509)[0].cert_info[0].validity[0].notBefore
		b=Membio()
		libcrypto.ASN1_TIME_print(b.bio,asn1date)
		return datetime.strptime(str(b),"%b %d %H:%M:%S %Y %Z").replace(tzinfo=utc)
	@property
	def endDate(self):
		""" Certificate validity period end date """
		# Need deep poke into certificate structure (x)->cert_info->validity->notAfter
		global utc
		asn1date=cast(self.cert,_px509)[0].cert_info[0].validity[0].notAfter
		b=Membio()
		libcrypto.ASN1_TIME_print(b.bio,asn1date)
		return datetime.strptime(str(b),"%b %d %H:%M:%S %Y %Z").replace(tzinfo=utc)
	def check_ca(self):
		""" Returns True if certificate is CA certificate """
		return libcrypto.X509_check_ca(self.cert)>0
class X509Store(object):
	"""
		Represents trusted certificate store. Can be used to lookup CA 
		certificates to verify

		@param file - file with several certificates and crls 
				to load into store
		@param dir - hashed directory with certificates and crls
		@param default - if true, default verify location (directory) 
			is installed

	"""
	def __init__(self,file=None,dir=None,default=False):
		"""
		Creates X509 store and installs lookup method. Optionally initializes 
		by certificates from given file or directory.
		"""
		#
		# Todo - set verification flags
		# 
		self.store=libcrypto.X509_STORE_new()
		if self.store is None:
			raise X509Error("allocating store")
		lookup=libcrypto.X509_STORE_add_lookup(self.store,libcrypto.X509_LOOKUP_file())
		if lookup is None:
			raise X509Error("error installing file lookup method")
		if (file is not None):
			if not libcrypto.X509_LOOKUP_ctrl(lookup,1,file,1,None)>0:
				raise X509Error("error loading trusted certs from file "+file)
		lookup=libcrypto.X509_STORE_add_lookup(self.store,libcrypto.X509_LOOKUP_hash_dir())
		if lookup is None:
			raise X509Error("error installing hashed lookup method")
		if dir is not None:
			if not libcrypto.X509_LOOKUP_ctrl(lookup,2,dir,1,None)>0:
				raise X509Error("error adding hashed  trusted certs dir "+dir)
		if default:
			if not libcrypto.X509_LOOKUP_ctrl(lookup,2,None,3,None)>0:
				raise X509Error("error adding default trusted certs dir ")
	def add_cert(self,cert):
		"""
		Explicitely adds certificate to set of trusted in the store
		@param cert - X509 object to add
		"""
		if not isinstance(cert,X509):
			raise TypeError("cert should be X509")
		libcrypto.X509_STORE_add_cert(self.store,cert.cert)
	def add_callback(self,callback):
		"""
		Installs callback function, which would receive detailed information
		about verified ceritificates
		"""
		raise NotImplementedError
	def setflags(self,flags):
		"""
		Set certificate verification flags.
		@param flags - integer bit mask. See OpenSSL X509_V_FLAG_* constants
		"""
		libcrypto.X509_STORE_set_flags(self.store,flags)	
	def setpurpose(self,purpose):
		"""
		Sets certificate purpose which verified certificate should match
		@param purpose - number from 1 to 9 or standard strind defined in Openssl
		possible strings - sslcient,sslserver, nssslserver, smimesign,smimeencrypt, crlsign, any,ocsphelper
		"""
		if isinstance(purpose,str):
			purp_no=X509_PURPOSE_get_by_sname(purpose)
			if purp_no <=0:
				raise X509Error("Invalid certificate purpose '"+purpose+"'")
		elif isinstance(purpose,int):
			purp_no = purpose
		if libcrypto.X509_STORE_set_purpose(self.store,purp_no)<=0:
			raise X509Error("cannot set purpose")
	def setdepth(self,depth):
		"""
		Sets the verification depth i.e. max length of certificate chain
		which is acceptable
		"""
		libcrypto.X509_STORE_set_depth(self.store,depth)
	def settime(self, time):
		"""
		Set point in time used to check validity of certificates for
		Time can be either python datetime object or number of seconds
		sinse epoch
		"""
		if isinstance(time,datetime.datetime) or isinstance(time,datetime.date):
			d=int(time.strftime("%s"))
		elif isinstance(time,int):
			pass
		else:
			raise TypeError("datetime.date, datetime.datetime or integer is required as time argument")
		raise NotImplementedError
class StackOfX509(object):
	"""
	Implements OpenSSL STACK_OF(X509) object.
	It looks much like python container types
	"""
	def __init__(self,certs=None,ptr=None,disposable=True):
		"""
		Create stack
		@param certs - list of X509 objects. If specified, read-write
			stack is created and populated by these certificates
		@param ptr - pointer to OpenSSL STACK_OF(X509) as returned by
			some functions
		@param disposable - if True, stack created from object, returned
				by function is copy, and can be modified and need to be
				freeid. If false, it is just pointer into another
				structure i.e. CMS_ContentInfo
		"""
		if  ptr is None:
			self.need_free = True
			self.ptr=libcrypto.sk_new_null()
			if certs is not None:
				for crt in certs:
					self.append(crt)
		elif certs is not None:
				raise ValueError("cannot handle certs an ptr simultaneously")
		else:
			self.need_free = disposable
			self.ptr=ptr
	def __len__(self):
		return libcrypto.sk_num(self.ptr)
	def __getitem__(self,index):
		if index <0 or index>=len(self):
			raise IndexError
		p=libcrypto.sk_value(self.ptr,index)
		return X509(ptr=libcrypto.X509_dup(p))
	def __setitem__(self,index,value):
		if not self.need_free:
			raise ValueError("Stack is read-only")
		if index <0 or index>=len(self):
			raise IndexError
		if not isinstance(value,X509):
			raise TypeError('StackOfX508 can contain only X509 objects')
		p=libcrypto.sk_value(self.ptr,index)
		libcrypto.sk_set(self.ptr,index,libcrypto.X509_dup(value.cert))
		libcrypto.X509_free(p)
	def __delitem__(self,index):	
		if not self.need_free:
			raise ValueError("Stack is read-only")
		if index <0 or index>=len(self):
			raise IndexError
		p=libcrypto.sk_delete(self.ptr,index)
		libcrypto.X509_free(p)
	def __del__(self):
		if self.need_free:
			libcrypto.sk_pop_free(self.ptr,libcrypto.X509_free)
	def append(self,value):
		if not self.need_free:
			raise ValueError("Stack is read-only")
		if not isinstance(value,X509):
			raise TypeError('StackOfX508 can contain only X509 objects')
		libcrypto.sk_push(self.ptr,libcrypto.X509_dup(value.cert))
libcrypto.i2a_ASN1_INTEGER.argtypes=(c_void_p,c_void_p)
libcrypto.ASN1_STRING_print_ex.argtypes=(c_void_p,c_void_p,c_long)
libcrypto.PEM_read_bio_X509.restype=c_void_p
libcrypto.PEM_read_bio_X509.argtypes=(c_void_p,POINTER(c_void_p),c_void_p,c_void_p)
libcrypto.PEM_write_bio_X509.restype=c_int
libcrypto.PEM_write_bio_X509.argtypes=(c_void_p,c_void_p)
libcrypto.ASN1_TIME_print.argtypes=(c_void_p,c_void_p)
libcrypto.ASN1_INTEGER_get.argtypes=(c_void_p,)
libcrypto.ASN1_INTEGER_get.restype=c_long
libcrypto.X509_get_serialNumber.argtypes=(c_void_p,)
libcrypto.X509_get_serialNumber.restype=c_void_p
libcrypto.X509_NAME_ENTRY_get_object.restype=c_void_p
libcrypto.X509_NAME_ENTRY_get_object.argtypes=(c_void_p,)
libcrypto.OBJ_obj2nid.argtypes=(c_void_p,)
libcrypto.X509_NAME_get_entry.restype=c_void_p
libcrypto.X509_NAME_get_entry.argtypes=(c_void_p,c_int)
libcrypto.X509_STORE_new.restype=c_void_p
libcrypto.X509_STORE_add_lookup.restype=c_void_p
libcrypto.X509_STORE_add_lookup.argtypes=(c_void_p,c_void_p)
libcrypto.X509_LOOKUP_file.restype=c_void_p
libcrypto.X509_LOOKUP_hash_dir.restype=c_void_p
libcrypto.X509_LOOKUP_ctrl.restype=c_int
libcrypto.X509_LOOKUP_ctrl.argtypes=(c_void_p,c_int,c_char_p,c_long,POINTER(c_char_p))
libcrypto.X509_EXTENSION_dup.argtypes=(c_void_p,)
libcrypto.X509_EXTENSION_dup.restype=POINTER(_x509_ext)
libcrypto.X509V3_EXT_print.argtypes=(c_void_p,POINTER(_x509_ext),c_long,c_int)
libcrypto.X509_get_ext.restype=c_void_p
libcrypto.X509_get_ext.argtypes=(c_void_p,c_int)
libcrypto.X509V3_EXT_print.argtypes=(c_void_p,POINTER(_x509_ext),c_long,c_int)
libcrypto.sk_set.argtypes=(c_void_p,c_int,c_void_p)
libcrypto.sk_set.restype=c_void_p
libcrypto.sk_value.argtypes=(c_void_p,c_int)
libcrypto.sk_value.restype=c_void_p
libcrypto.X509_dup.restype=c_void_p
libcrypto.sk_new_null.restype=c_void_p
libcrypto.X509_dup.argtypes=(c_void_p,)
libcrypto.X509_NAME_hash.restype=c_long
libcrypto.X509_NAME_hash.argtypes=(c_void_p,)
