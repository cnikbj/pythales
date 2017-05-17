#!/usr/bin/env python

import getopt
import sys
import socket
import struct 

from tracetools.tracetools import trace
from collections import OrderedDict
from Crypto.Cipher import DES, DES3
from binascii import hexlify, unhexlify
from pynblock.tools import raw2str, raw2B, B2raw, xor, get_visa_pvv


def get_key_check_value(key, kcv_length=6):
    """
    Get DES key check value
    """
    cipher = DES3.new(B2raw(key), DES3.MODE_ECB)
    encrypted = raw2B(cipher.encrypt(B2raw(b'00000000000000000000000000000000')))

    return encrypted[:kcv_length]


class DC():
    def __init__(self, data):
        self.data = data
        self.fields = OrderedDict()

        # TPK
        if self.data[0:1] in [b'U', b'T', b'S']:
            field_size = 33            
            self.fields['TPK'] = self.data[0:field_size]
            self.data = self.data[field_size:]

        # PVK
        if self.data[0:1] in [b'U']:
            field_size = 33            
            self.fields['PVK Pair'] = self.data[0:field_size]
            self.data = self.data[field_size:]
        else:
            field_size = 32
            self.fields['PVK Pair'] = self.data[0:field_size]
            self.data = self.data[field_size:]

        # PIN block
        field_size = 16
        self.fields['PIN block'] = self.data[0:field_size]
        self.data = self.data[field_size:]

        # PIN block format code
        field_size = 2
        self.fields['PIN block format code'] = self.data[0:field_size]
        self.data = self.data[field_size:]

        # Account Number
        field_size = 12
        self.fields['Account Number'] = self.data[0:field_size]
        self.data = self.data[field_size:]

        # PVKI
        field_size = 1
        self.fields['PVKI'] = self.data[0:field_size]
        self.data = self.data[field_size:]

        # PVV
        field_size = 4
        self.fields['PVV'] = self.data[0:field_size]
        self.data = self.data[field_size:]


class CA():
    def __init__(self, data):
        self.data = data
        self.fields = OrderedDict()

        # TPK
        if self.data[0:1] in [b'U', b'T', b'S']:
            field_size = 33
            self.fields['TPK'] = self.data[0:field_size]
            self.data = self.data[field_size:]

        # Destination Key
        if self.data[0:1] in [b'U', b'T', b'S']:
            field_size = 33
            self.fields['Destination Key'] = self.data[0:field_size]
            self.data = self.data[field_size:]

        # Maximum PIN Length
        field_size = 2
        self.fields['Maximum PIN Length'] = self.data[0:field_size]
        self.data = self.data[field_size:]

        # Source PIN block
        field_size = 16
        self.fields['Source PIN block'] = self.data[0:field_size]
        self.data = self.data[field_size:]

        # Source PIN block format
        field_size = 2
        self.fields['Source PIN block format'] = self.data[0:field_size]
        self.data = self.data[field_size:]

        # Destination PIN block format
        field_size = 2
        self.fields['Destination PIN block format'] = self.data[0:field_size]
        self.data = self.data[field_size:]

        # Account Number
        field_size = 12
        self.fields['Account Number'] = self.data[0:field_size]
        self.data = self.data[field_size:]


class CY():
    def __init__(self, data):
        self.data = data
        self.fields = OrderedDict()

        # CVK
        if self.data[0:1] in [b'U', b'T', b'S']:
            field_size = 33
            self.fields['CVK'] = self.data[0:field_size]
            self.data = self.data[field_size:]

        # CVV
        field_size = 3
        self.fields['CVV'] = self.data[0:field_size]
        self.data = self.data[field_size:]

        # Primary Account Number
        delimiter_index = 0
        for byte in self.data:
            if byte == 59:  # b';'
                break
            delimiter_index += 1

        self.fields['Primary Account Number'] = self.data[0:delimiter_index]
        self.data = self.data[delimiter_index + 1:]

        # Expiration Date
        field_size = 4
        self.fields['Expiration Date'] = self.data[0:field_size]
        self.data = self.data[field_size:]

        # Service Code
        field_size = 3
        self.fields['Service Code'] = self.data[0:field_size]
        self.data = self.data[field_size:]


class Message:
    def __init__(self, data=None, header=None):
        if data:
            """
            Incoming message
            """
            self.length = struct.unpack_from("!H", data[:2])[0]
            if(self.length != len(data) - 2):
                raise ValueError('Expected message of length {0} but actual received message length is {1}'.format(self.length, len(data) - 2))
    
            if header:
                for h, d in zip(header, data[2:]):
                    if h != d:
                        raise ValueError('Invalid header')
                self.header = header 

            if header:
                self.data = data[2 + len(header) : ]
            else:
                self.data = data[2:]

            self.command_code = self.data[:2]
            
            if self.command_code == b'DC':
                self.fields = DC(self.data[2:]).fields
            elif self.command_code == b'CA':
                self.fields = CA(self.data[2:]).fields
            elif self.command_code == b'CY':
                self.fields = CY(self.data[2:]).fields
            else:
                self.fields = None

        else:
            """
            Outgoing message
            """
            self.header = header
            self.fields = OrderedDict()

    
    def get_command_code(self):
        """
        """
        return self.command_code


    def get_length(self):
        """
        """
        return self.length


    def get_data(self):
        """
        """
        return self.data


    def build(self):
        """
        Build the outgoing message (legacy)
        """
        data = b''
        for key, value in self.fields.items():
            data += value

        if self.header:
            return struct.pack("!H", len(self.header) + len(data)) + self.header + data
        else:
            return struct.pack("!H", len(data)) + data


    def trace(self):
        """
        """
        if not self.fields:
            return ''

        width = 0
        for key, value in self.fields.items():
            if len(key) > width:
                width = len(key)

        dump = ''
        for key, value in self.fields.items():
            dump = dump + '\t[' + key.ljust(width, ' ') + ']: [' + value.decode('utf-8') + ']\n'
        return dump


class HSM:
    def __init__(self, port=None, header=None, key=None, debug=False):
        self.firmware_version = '0007-E000'

        if port:
            self.port = port
        else:
            self.port = 1500

        if header:
            self.header = bytes(header, 'utf-8')
        else:
            self.header = b''

        if key:
            self.LMK = bytes.fromhex(key)
        else:
            self.LMK = bytes.fromhex('deadbeef deadbeef deadbeef deadbeef')
        
        self.cipher = DES3.new(self.LMK, DES3.MODE_ECB)
        self.debug = debug

    
    def info(self):
        """
        """
        dump = ''
        dump += 'LMK: {}\n'.format(raw2str(self.LMK))
        dump += 'Firmware version: {}\n'.format(self.firmware_version)
        if self.header:
            dump += 'Message header: {}\n'.format(self.header.decode('utf-8'))
        return dump


    def _debug_trace(self, data):
        """
        """
        if self.debug:
            print('\tDEBUG: {}\n'.format(data))


    def _init_connection(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.bind(('', self.port))   
            self.sock.listen(5)
            print(self.info())
            print('Listening on port {}'.format(self.port))
        except OSError as msg:
            print('Error starting server: {}'.format(msg))
            sys.exit()
        

    def run(self):
        self._init_connection()

        while True:
            try:
                conn, addr = self.sock.accept()
                client_name = addr[0] + ':' + str(addr[1])
                print ('Connected client: {}'.format(client_name))

                while True:
                    data = conn.recv(4096)
                    if len(data):
                        trace('<< {} bytes received from {}: '.format(len(data), client_name), data)

                    try:
                        request = Message(data, header=self.header)
                        print(request.trace())
                    except ValueError as e:
                        print(e)
                        continue

                    response = self.get_response(request)
                    response_data = response.build()
                    conn.send(response_data)

                    trace('>> {} bytes sent to {}:'.format(len(response_data), client_name), response_data)
                    print(response.trace())
    
            except KeyboardInterrupt:
                break
            
            except:
                print('RUNTIME ERROR: {}\n'.format(sys.exc_info()[1]))
                print('Disconnected client: {}'.format(client_name))
                conn.close()
                continue

        self.sock.close()
        print('Exit')


    def _get_clear_key(self, encrypted_key):
        """
        Decrypt the key, encrypted under LMK
        """
        if encrypted_key[0:1] in [b'U']:
            return self.cipher.decrypt(B2raw(encrypted_key[1:]))
        else:
            return self.cipher.decrypt(B2raw(encrypted_key))


    def _decrypt_pinblock(self, encrypted_pinblock, encrypted_terminal_key):
        """
        Decrypt pin block
        """
        clear_terminal_key = self._get_clear_key(encrypted_terminal_key)
        cipher = DES3.new(clear_terminal_key, DES3.MODE_ECB)
        decrypted_pinblock = cipher.decrypt(B2raw(encrypted_pinblock))
        return raw2B(decrypted_pinblock)


    def _get_clear_pin(self, pinblock, account_number):
        """
        Calculate the clear PIN from provided PIN block and account_number, which is the 12 right-most digits of card account number, excluding check digit
        """
        raw_pinblock = bytes.fromhex(pinblock.decode('utf-8'))
        raw_acct_num = bytes.fromhex((b'0000' + account_number).decode('utf-8'))
            
        pin_str = xor(raw2B(raw_pinblock), raw2B(raw_acct_num)).decode('utf-8')
        pin_length = int(pin_str[:2], 16)
        
        if pin_length >= 4 and pin_length < 9:
            pin = pin_str[2:2+pin_length]            
            try:
                int(pin)
            except ValueError:
                raise ValueError('PIN contains non-numeric characters')
            return bytes(pin, 'utf-8')
        else:
            raise ValueError('Incorrect PIN length: {}'.format(pin_length))


    def _get_visa_cvv(self, account_number, exp_date, service_code, CVK):
        """
        """
        if len(CVK) != 32:
            raise ValueError('Incorrect key length')
        
        tsp = exp_date + service_code + b'000000000'
        des_cipher = DES.new(B2raw(CVK[:16]))
        des3_cipher = DES3.new(B2raw(CVK), DES3.MODE_ECB)
        
        block1 = xor(raw2B(des_cipher.encrypt(B2raw(account_number))), tsp)
        block2 = des3_cipher.encrypt(B2raw(block1))

        return self._get_digits_from_string(raw2str(block2), 3)


    def verify_cvv(self, request):
        """
        Get response to CY command
        """
        response =  Message(data=None, header=self.header)
        response.fields['Response Code'] = b'CZ'

        CVK = request.fields['CVK']
        if CVK[0:1] in [b'U']:
            CVK = CVK[1:]
        
        cvv = self._get_visa_cvv(request.fields['Primary Account Number'], request.fields['Expiration Date'], request.fields['Service Code'], CVK)
        if bytes(cvv, 'utf-8') == request.fields['CVV']:
            response.fields['Error Code'] = b'00'
        else:
            self._debug_trace('CVV mismatch: {} != {}'.format(cvv, request.fields['CVV'].decode('utf-8')))
            response.fields['Error Code'] = b'01'
            
        return response


    def _get_digits_from_string(self, cyphertext, length=4):
        """
        Extract PVV/CVV digits from the cyphertext (HEX-encoded string)
        """
        digits = ''
    
        """
        The algorigthm is used for PVV and CVV calculation.

        1. The cyphertext is scanned from left to right. Decimal digits are
        selected during the scan until the needed number of decimal digits is found. 
        Each selected digit is placed from left to right according to the order
        of selection. If needed number of decimal digits is found (four in case of PVV, 
        three in case of CVV), those digits are the PVV or CVV.
        """
        for c in cyphertext:
            if len(digits) >= length:
                break
    
            try:
                int(c)
                digits += c
            except ValueError:
                continue
    
        """
        2. If, at the end of the first scan, less than four decimal digits
        have been selected, a second scan is performed from left to right.
        During the second scan, all decimal digits are skipped and only nondecimal
        digits can be processed. Nondecimal digits are converted to decimal
        digits by subtracting 10. The process proceeds until four digits of
        PVV are found.
        """
        if len(digits) < length:
            for c in cyphertext:
                if len(digits) >= length:
                    break
    
                if (int(c, 16) - 10) >= 0:
                    digits += str(int(c, 16) - 10)
    
        return digits


    def verify_pin(self, request):
        """
        Get response to DC command
        """
        decrypted_pinblock = self._decrypt_pinblock(request.fields['PIN block'], request.fields['TPK'])
        response =  Message(data=None, header=self.header)
        response.fields['Response Code'] = b'DD'

        try:
            pin = self._get_clear_pin(decrypted_pinblock, request.fields['Account Number'])
            pvv = get_visa_pvv(request.fields['Account Number'], request.fields['PVKI'], pin[:4], request.fields['PVK Pair'])
            if pvv == request.fields['PVV']:
                response.fields['Error Code'] = b'00'
            else:
                self._debug_trace('PVV mismatch: {} != {}'.format(pvv.decode('utf-8'), request.fields['PVV'].decode('utf-8')))
                response.fields['Error Code'] = b'01'
            
            return response

        except ValueError:
            response.fields['Error Code'] = b'01'
            return response


    def translate_pinblock(self, request):
        """
        Get response to CA command (Translate PIN from TPK to ZPK)
        TODO: return Message object
        """
        response_code = b'CB00'
        pinblock_format = request.fields['Destination PIN block format']

        if request.fields['Destination PIN block format'] != request.fields['Source PIN block format']:
            raise ValueError('Cannot translate PIN block from format {} to format {}'.format(request.fields['Source PIN block format'].decode('utf-8'), request.fields['Destination PIN block format'].decode('utf-8')))

        if request.fields['Source PIN block format'] != b'01':
            raise ValueError('Unsupported PIN block format: {}'.format(request.fields['Source PIN block format'].decode('utf-8')))

        decrypted_pinblock = self._decrypt_pinblock(request.fields['Source PIN block'], request.fields['TPK'])
        pin_length = decrypted_pinblock[0:2]

        if request.fields['Destination Key'][0:1] in [b'U']:
            destination_key = request.fields['Destination Key'][1:]
        else:
            destination_key = request.fields['Destination Key']

        cipher = DES3.new(B2raw(destination_key), DES3.MODE_ECB)
        translated_pin_block = cipher.encrypt(B2raw(decrypted_pinblock))

        response = Message(data=None, header=self.header)
        response.fields['Response Code'] = b'CB'
        response.fields['Error Code'] = b'00'
        response.fields['PIN Length'] = decrypted_pinblock[0:2]
        response.fields['Destination PIN Block'] = raw2B(translated_pin_block)
        response.fields['Destination PIN Block format'] = pinblock_format

        return response


    def get_diagnostics_data(self):
        """
        Get response to NC command
        """
        response = Message(data=None, header=self.header)
        response.fields['Response Code'] = b'ND' 
        response.fields['Error Code'] = b'00' 
        response.fields['LMK Check Value'] = get_key_check_value(raw2B(self.LMK), 16)
        response.fields['Firmware Version'] = bytes(self.firmware_version, 'utf-8')
        return response


    def get_response(self, request):
        """
        """
        rqst_command_code = request.get_command_code()
        if rqst_command_code == b'NC':
            return self.get_diagnostics_data()
        elif rqst_command_code == b'DC':
            return self.verify_pin(request)
        elif rqst_command_code == b'CA':
            return self.translate_pinblock(request)
        elif rqst_command_code == b'CY':
            return self.verify_cvv(request)
        else:
            response = Message(data=None, header=self.header)
            response.fields['Response Code'] = b'ZZ'
            response.fields['Error Code'] = b'00'
            return response


def show_help(name):
    """
    Show help and basic usage
    """
    print('Usage: python3 {} [OPTIONS]... '.format(name))
    print('Thales HSM command simulator')
    print('  -p, --port=[PORT]\t\tTCP port to listen, 1500 by default')
    print('  -k, --key=[KEY]\t\tTCP port to listen, 1500 by default')
    print('  -h, --header=[HEADER]\t\tmessage header, empty by default')
    print('  -d, --debug\t\t\tEnable debug mode (show CVV/PVV mismatch etc)')


if __name__ == '__main__':
    port = None
    header = ''
    key = None
    debug = False

    optlist, args = getopt.getopt(sys.argv[1:], 'h:p:k:d', ['header=', 'port=', 'key=', 'debug'])
    for opt, arg in optlist:
        if opt in ('-h', '--header'):
            header = arg
        elif opt in ('-p', '--port'):
            try:
                port = int(arg)
            except ValueError:
                print('Invalid TCP port: {}'.format(arg))
                sys.exit()
        elif opt in ('-k', '--key'):
            key = arg
        elif opt in ('-d', '--debug'):
            debug = True
        else:
            show_help(sys.argv[0])
            sys.exit()

    hsm = HSM(port=port, header=header, key=key, debug=debug)
    hsm.run()
