#!/usr/bin/env python

import unittest

from pythales.hsm import get_key_check_value, HSM, Message, CA, CY, DC


class TestCryptoTools(unittest.TestCase):
    def test_get_key_check_value_default_kcv_length(self):
        self.assertEqual(get_key_check_value(b'E6F1081FEA4C402CC192B65DE367EC3E'), b'212CF9')

    def test_get_key_check_value_4(self):
        self.assertEqual(get_key_check_value(b'E6F1081FEA4C402CC192B65DE367EC3E', 4), b'212C')

    def test_get_key_check_value_6(self):
        self.assertEqual(get_key_check_value(b'E6F1081FEA4C402CC192B65DE367EC3E', 6), b'212CF9')

    def test_get_key_check_value_16(self):
        self.assertEqual(get_key_check_value(b'E6F1081FEA4C402CC192B65DE367EC3E', 16), b'212CF9158251CDD3')


class TestMessageClass(unittest.TestCase):
    """
    """
    def test_get_length(self):
        m = Message(b'\x00\x06SSSS00')
        self.assertEqual(m.get_length(), 6)


    def test_get_length_incorrect(self):
        with self.assertRaisesRegex(ValueError, 'Expected message of length 6 but actual received message length is 2'):
            m = Message(b'\x00\x0600')
            self.assertEqual(m.get_length(), 6)


    def test_invalid_message_header(self):
        data = b'\x00\x06SSSS00'
        header = b'XDXD'
        with self.assertRaisesRegex(ValueError, 'Invalid header'):
            m = Message(data, header)


    def test_valid_message_header(self):
        data = b'\x00\x07IDDQD77'
        header = b'IDDQD'
        self.assertTrue(Message(data, header))


    def test_get_data(self):
        data = b'\x00\x07HDRDATA'
        header = b'HDR'
        m = Message(data, header)
        self.assertEqual(m.get_data(), b'DATA')


    def test_get_command_code(self):
        data = b'\x00\x07HDRDCXX'
        header = b'HDR'
        m = Message(data, header)
        self.assertEqual(m.get_command_code(), b'DC')    


    def test_outgoing_message(self):
        m = Message(data=None, header=b'XXXX')
        m.fields['Command Code'] = b'NG'
        m.fields['Response Code'] = b'00'
        m.fields['Data'] = b'7444321'
        self.assertEqual(m.build(), b'\x00\x0FXXXXNG007444321')


    def test_outgoing_message_no_header(self):
        m = Message(data=None, header=None)
        m.fields['Command Code'] = b'NG'
        m.fields['Response Code'] = b'00'
        m.fields['Data'] = b'7444321'
        self.assertEqual(m.build(), b'\x00\x0BNG007444321')


class TestDC(unittest.TestCase):
    """
    DC command received:
    00 6a 53 53 53 53 44 43 55 44 45 41 44 42 45 45         .jSSSSDCUDEADBEE
    46 44 45 41 44 42 45 45 46 44 45 41 44 42 45 45         FDEADBEEFDEADBEE
    46 44 45 41 44 42 45 45 46 31 32 33 34 35 36 37         FDEADBEEF1234567
    38 39 30 41 42 43 44 45 46 31 32 33 34 35 36 37         890ABCDEF1234567
    38 39 30 41 42 43 44 45 46 32 42 36 38 37 41 45         890ABCDEF2B687AE
    46 43 33 34 42 31 41 38 39 30 31 30 30 31 31 32         FC34B1A890100112
    33 34 35 36 37 38 39 31 38 37 32 33                     345678918723
    """
    def setUp(self):
        data = b'UDEADBEEFDEADBEEFDEADBEEFDEADBEEF1234567890ABCDEF1234567890ABCDEF2B687AEFC34B1A890100112345678918723'
        self.dc = DC(data)
        self.hsm = HSM(header='SSSS')
        
    def test_tpk_parsed(self):
        self.assertEqual(self.dc.fields['TPK'], b'UDEADBEEFDEADBEEFDEADBEEFDEADBEEF')

    def test_pvk_parsed(self):
        self.assertEqual(self.dc.fields['PVK Pair'], b'1234567890ABCDEF1234567890ABCDEF')

    def test_pinblock_parsed(self):
        self.assertEqual(self.dc.fields['PIN block'], b'2B687AEFC34B1A89')

    def test_pinblock_format_code_parsed(self):
        self.assertEqual(self.dc.fields['PIN block format code'], b'01')

    def test_account_number_parsed(self):
        self.assertEqual(self.dc.fields['Account Number'], b'001123456789')

    def test_pvki_parsed(self):
        self.assertEqual(self.dc.fields['PVKI'], b'1')

    def test_pvv_parsed(self):
        self.assertEqual(self.dc.fields['PVV'], b'8723')


class TestCA(unittest.TestCase):
    """
    18:47:19.371109 << 108 bytes received from 192.168.56.101:33284: 
        00 6a 53 53 53 53 43 41 55 45 44 34 41 33 35 44         .jSSSSCAUED4A35D
        35 32 43 39 30 36 33 41 31 45 44 34 41 33 35 44         52C9063A1ED4A35D
        35 32 43 39 30 36 33 41 31 55 44 33 39 44 33 39         52C9063A1UD39D39
        45 42 37 43 39 33 32 43 46 33 36 37 43 39 37 43         EB7C932CF367C97C
        35 42 31 30 42 32 43 31 39 35 31 32 37 44 46 33         5B10B2C195127DF3
        36 36 42 38 36 41 45 32 44 39 41 37 30 31 30 33         66B86AE2D9A70103
        35 35 32 30 30 30 30 30 30 30 31 32                     552000000012
    """
    def setUp(self):
        data = b'UED4A35D52C9063A1ED4A35D52C9063A1UD39D39EB7C932CF367C97C5B10B2C195127DF366B86AE2D9A70103552000000012'
        self.ca = CA(data)
        self.hsm = HSM(header='SSSS')

    def test_tpk_parsed(self):
        self.assertEqual(self.ca.fields['TPK'], b'UED4A35D52C9063A1ED4A35D52C9063A1')

    def test_dest_key_parsed(self):
        self.assertEqual(self.ca.fields['Destination Key'], b'UD39D39EB7C932CF367C97C5B10B2C195')

    def test_max_pin_length_parsed(self):
        self.assertEqual(self.ca.fields['Maximum PIN Length'], b'12')

    def test_source_pin_block_parsed(self):
        self.assertEqual(self.ca.fields['Source PIN block'], b'7DF366B86AE2D9A7')

    def test_source_pin_block_format_parsed(self):
        self.assertEqual(self.ca.fields['Source PIN block format'], b'01')

    def test_dest_pin_block_format_parsed(self):
        self.assertEqual(self.ca.fields['Destination PIN block format'], b'03')

    def test_account_number_parsed(self):
        self.assertEqual(self.ca.fields['Account Number'], b'552000000012')


class TestCY(unittest.TestCase):
    """
    00 42 53 53 53 53 43 59 55 34 34 39 44 46 31 36         .BSSSSCYU449DF16
    37 39 46 34 41 34 45 30 36 39 35 45 39 39 44 39         79F4A4E0695E99D9
    32 31 41 32 35 33 44 43 42 30 30 30 38 39 39 30         21A253DCB0008990
    30 31 31 32 33 34 35 36 37 38 39 30 3b 31 38 30         011234567890;180
    39 32 30 31                                             9201

    """
    def setUp(self):
        data = b'U449DF1679F4A4E0695E99D921A253DCB0008990011234567890;1809201'
        self.cy = CY(data)
        self.hsm = HSM(header='SSSS')

    def test_cvk_parsed(self):
        self.assertEqual(self.cy.fields['CVK'], b'U449DF1679F4A4E0695E99D921A253DCB')

    def test_cvv_parsed(self):
        self.assertEqual(self.cy.fields['CVV'], b'000')

    def test_account_number_parsed(self):
        self.assertEqual(self.cy.fields['Primary Account Number'], b'8990011234567890')

    def test_expiry_date_parsed(self):
        self.assertEqual(self.cy.fields['Expiration Date'], b'1809')

    def test_service_code_parsed(self):
        self.assertEqual(self.cy.fields['Service Code'], b'201')


class TestHSM(unittest.TestCase):
    def setUp(self):
        self.hsm = HSM(header='SSSS')

    def test_decrypt_pinblock(self):
        self.assertEqual(self.hsm._decrypt_pinblock(b'2B687AEFC34B1A89', b'UDEADBEEFDEADBEEFDEADBEEFDEADBEEF'), b'D694D2659AD26C2E')

    def test_get_clear_pin_1234(self):
        self.assertEqual(self.hsm._get_clear_pin(b'0412BCEEDCBA9876', b'881123456789'), b'1234')

    def test_get_clear_pin_non_numeric(self):
        with self.assertRaisesRegex(ValueError, 'PIN contains non-numeric characters'):
            self.hsm._get_clear_pin(b'041267EEDCBA9876', b'881123456789')

    def test_get_clear_pin_pin_length_9(self):
        with self.assertRaisesRegex(ValueError, 'Incorrect PIN length: 9'):
            self.hsm._get_clear_pin(b'091267EEDCBA9876', b'881123456789')

    def test_get_clear_pin_improper_length(self):
        with self.assertRaisesRegex(ValueError, 'Incorrect PIN length: 223'):
            self.hsm._get_clear_pin(b'DF1267EEDCBA9876', b'881123456789')

    """
    hsm._get_clear_key()
    """
    def test_decrypt_pinblock(self):
        self.assertEqual(self.hsm._get_clear_key(b'UDEADBEEFDEADBEEFDEADBEEFDEADBEEF'), b'6\x1e\xddt\xa1\xb4\xab\xc16\x1e\xddt\xa1\xb4\xab\xc1')


    """
    hsm._get_digits_from_string()
    """
    def test_get_digits_from_string(self):
        self.assertEqual(self.hsm._get_digits_from_string('59EF34AD722C0556F7F6FBD4A76D38E6', 4), '5934')

    def test_get_pvv_digits_from_mixed_string(self):
        self.assertEqual(self.hsm._get_digits_from_string('EEFADCFFFBD7ADECAB9FBB', 4), '7944')

    def test_get_digits_from_string_letters_only(self):
        self.assertEqual(self.hsm._get_digits_from_string('EFADCFFFBDADECABFBB', 4), '4503')

    def test_get_digits_from_string_letters_only_3(self):
        self.assertEqual(self.hsm._get_digits_from_string('EFADCFFFBDADECABFBB', 3), '450')

    """
    hsm._get_visa_cvv()
    """
    def test_get_visa_cvv(self):
        self.assertEqual(self.hsm._get_visa_cvv(b'4433678298261175', b'0916', b'101', b'4C37C8319D76ADAB58D9431543C2165B'), '478')

    """
    hsm.translate_pinblock()
    """
    def test_translate_pinblock_different_pinblock_formats(self):
        data = b'UED4A35D52C9063A1ED4A35D52C9063A1UD39D39EB7C932CF367C97C5B10B2C195127DF366B86AE2D9A70103552000000012'
        self.ca = CA(data)
        with self.assertRaisesRegex(ValueError, 'Cannot translate PIN block from format 01 to format 03'):
            self.hsm.translate_pinblock(self.ca)

    def test_translate_pinblock_unsupported_format(self):
        data = b'UED4A35D52C9063A1ED4A35D52C9063A1UD39D39EB7C932CF367C97C5B10B2C195127DF366B86AE2D9A70303552000000012'
        self.ca = CA(data)
        with self.assertRaisesRegex(ValueError, 'Unsupported PIN block format: 03'):
            self.hsm.translate_pinblock(self.ca)

    def test_translate_pinblock(self):
        data = b'UED4A35D52C9063A1ED4A35D52C9063A1UD39D39EB7C932CF367C97C5B10B2C195127DF366B86AE2D9A70101552000000012'
        self.ca = CA(data)
        response = self.hsm.translate_pinblock(self.ca)
        self.assertEqual(response.build(), b'\x00\x1cSSSSCB0004EEBCB810144AEC3301')   

    """
    User-defined key
    """
    def test_user_defined_key_wrong_key_size(self):
        with self.assertRaises(ValueError):
            self.hsm = HSM(key='DEADBEAF')

    def test_user_defined_key_value(self):
        with self.assertRaises(ValueError):
            self.hsm = HSM(key='iddqdeef deadbeef deadbeef deadbeef')

if __name__ == '__main__':
    unittest.main()