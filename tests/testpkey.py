from ctypescrypto.pkey import PKey
import unittest

class TestReadPkey(unittest.TestCase):
	def test_unencrypted_pem(self):
		rsa="""-----BEGIN PRIVATE KEY-----
MIICdQIBADANBgkqhkiG9w0BAQEFAASCAl8wggJbAgEAAoGBAL9CzVZu9bczTmB8
776pPUoPo6WbAfwQqqiGrj91bk2mYE+MNLo4yIQH45IcwGzkyS8+YyQJf8Bux5BC
oZ2nwzXm5+JZkxkN1mtMzit2D7/hHmrZLoSbr0sxXFrD4a35RI4hXnSK9Sk01sXA
Te2OgHzm5nk1sG97G6SFq7CHe3gvAgMBAAECgYAgGV8K7Y5xk7vIt88oyZCOuHc3
mP9JRabOp+PgpJ3BjHXHg/lpc5Q7jHNmF0s4O2GEe0z6RFnbevwlOvmS0xAQ1hpg
5TnVVkiZvcJeQaZqWIlEOaLqA12YdhSyorfB6p3tfQ7ZmQusg3SCsru5kPJV4sm0
I+MuRCQZWSzIqelloQJBAPbtScJI0lXx8sktntZi69cAVvLtz5z1T7bZwFakNkNE
SUCjNc/hEEI6/1LScV8Kx9kgQ0+W8smu+GyUDceyVFECQQDGSeS7cTmojkiPQxPB
zb0vS+Nfpq6oYsx+gn5TBgMeWIZZrtMEaUU2o+rwsjKBP/gy6D1zC2b4W5O/A/7a
1GR/AkBUQhYoKKc1UpExGtMXfrvRKrmAvatZeM/Rqi4aooAtpfCFEOw82iStJOqY
/VxYPRqCuaKeVvjT31O/4SlumihxAkBahRU0NKYbuoiJThfQ23lIBB7SZadKG4A7
KJs+j3oQ+lyqyFJwqxX7sazpIJBJzMgjhT24LTZenn++LbbEcz1FAkBmDmxoq7qO
Ao6uTm8fnkD4C836wS4mYAPqwRBK1JvnEXEQee9irf+ip89BAg74ViTcGF9lwJwQ
gOM+X5Db+3pK
-----END PRIVATE KEY-----
"""
		keytext="""Public-Key: (1024 bit)
Modulus:
    00:bf:42:cd:56:6e:f5:b7:33:4e:60:7c:ef:be:a9:
    3d:4a:0f:a3:a5:9b:01:fc:10:aa:a8:86:ae:3f:75:
    6e:4d:a6:60:4f:8c:34:ba:38:c8:84:07:e3:92:1c:
    c0:6c:e4:c9:2f:3e:63:24:09:7f:c0:6e:c7:90:42:
    a1:9d:a7:c3:35:e6:e7:e2:59:93:19:0d:d6:6b:4c:
    ce:2b:76:0f:bf:e1:1e:6a:d9:2e:84:9b:af:4b:31:
    5c:5a:c3:e1:ad:f9:44:8e:21:5e:74:8a:f5:29:34:
    d6:c5:c0:4d:ed:8e:80:7c:e6:e6:79:35:b0:6f:7b:
    1b:a4:85:ab:b0:87:7b:78:2f
Exponent: 65537 (0x10001)
"""
		key=PKey(privkey=rsa)
		self.assertIsNotNone(key.key)
		self.assertEqual(str(key),keytext)
	def test_unencrypted_pem_ec(self):
		pem="""-----BEGIN EC PRIVATE KEY-----
MHQCAQEEICpxup3qmbwffBBLrsZx7H7/i/+Wm7jTRttMM1KkaZ3DoAcGBSuBBAAK
oUQDQgAEVil1nlGelogimdpB8fO45icsdBt2QdYkAvhqdgCWLMG0D4Rj4oCqJcyG
2WH8J5+0DnGujfEA4TwJ90ECvLa2SA==
-----END EC PRIVATE KEY-----
"""
		keytext="""Public-Key: (256 bit)
pub: 
    04:56:29:75:9e:51:9e:96:88:22:99:da:41:f1:f3:
    b8:e6:27:2c:74:1b:76:41:d6:24:02:f8:6a:76:00:
    96:2c:c1:b4:0f:84:63:e2:80:aa:25:cc:86:d9:61:
    fc:27:9f:b4:0e:71:ae:8d:f1:00:e1:3c:09:f7:41:
    02:bc:b6:b6:48
ASN1 OID: secp256k1
"""
		
		key=PKey(privkey=pem)
		self.assertIsNotNone(key.key)
		self.assertEqual(str(key),keytext)
	def test_pubkey_pem(self):
		pub="""-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAEVil1nlGelogimdpB8fO45icsdBt2QdYk
AvhqdgCWLMG0D4Rj4oCqJcyG2WH8J5+0DnGujfEA4TwJ90ECvLa2SA==
-----END PUBLIC KEY-----
"""
		key=PKey(pubkey=pub)
		keytext="""Public-Key: (256 bit)
pub: 
    04:56:29:75:9e:51:9e:96:88:22:99:da:41:f1:f3:
    b8:e6:27:2c:74:1b:76:41:d6:24:02:f8:6a:76:00:
    96:2c:c1:b4:0f:84:63:e2:80:aa:25:cc:86:d9:61:
    fc:27:9f:b4:0e:71:ae:8d:f1:00:e1:3c:09:f7:41:
    02:bc:b6:b6:48
ASN1 OID: secp256k1
"""
		self.assertIsNotNone(key.key)	
		self.assertEqual(str(key),keytext)
	def test_compare(self):
		pem="""-----BEGIN EC PRIVATE KEY-----
MHQCAQEEICpxup3qmbwffBBLrsZx7H7/i/+Wm7jTRttMM1KkaZ3DoAcGBSuBBAAK
oUQDQgAEVil1nlGelogimdpB8fO45icsdBt2QdYkAvhqdgCWLMG0D4Rj4oCqJcyG
2WH8J5+0DnGujfEA4TwJ90ECvLa2SA==
-----END EC PRIVATE KEY-----
"""
		pub="""-----BEGIN PUBLIC KEY-----
MFYwEAYHKoZIzj0CAQYFK4EEAAoDQgAEVil1nlGelogimdpB8fO45icsdBt2QdYk
AvhqdgCWLMG0D4Rj4oCqJcyG2WH8J5+0DnGujfEA4TwJ90ECvLa2SA==
-----END PUBLIC KEY-----
"""
		key1=PKey(privkey=pem)
		self.assertIsNotNone(key1.key)
		key2=PKey(pubkey=pub)
		self.assertIsNotNone(key2.key)
		self.assertEqual(key1,key2)

if __name__ == "__main__":
	unittest.main()
