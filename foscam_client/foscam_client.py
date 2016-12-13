import socket as socket_lib
import os
import threading
from time import sleep
import datetime
import subprocess as sp
import numpy
from PIL import Image

import settings as settings

MAGIC_NUMBER_STR = 'FOSC'  # 4 byte
SESSION_ID_HEX = '735f6d65'  # 4 byte
# client to camera commands
LOGIN_COMMAND_HEX = '0c'
CHECK_LOGIN_COMMAND_HEX = '0f'
VIDEO_ON_COMMAND_HEX = '00'
# camera to client commands
LOGIN_CHECK_REPLAY_COMMAND_HEX = '0x1d'
VIDEO_IN_COMMAND_HEX = '1a'
PTZ_COMMAND_HEX = '0x64'
MOTION_DETECTION_COMMAND_HEX = '0x6f'

class FoscamClient:
    
    def __init__(self, ip, port, username, password, directory):
        self.ip = ip
        self.port = port
        self.username = username.encode('hex')
        self.password = password.encode('hex')
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.directory = directory
        self.socket, status = self.connect_to_camera()
        if status :
            print 'Successfully connected to the camera!' 
        else: 
            print 'NOT connected to the camera! Please check username and password.'
            quit()
    
    def create_header(self):
        header = 'SERVERPUSH / HTTP/1.1\r\n'
        header += 'Host: {}:{}\r\n'.format(self.ip, self.port)
        header += 'Accept:*/*\r\n'
        header += 'Connection: Close\r\n\r\n'
        return header 
    
    def create_login_command(self):
        login_command = self.add_padding(LOGIN_COMMAND_HEX, 4).decode('hex')
        login_command += MAGIC_NUMBER_STR
        login_command += self.add_padding('a4', 4).decode('hex')
        login_command += self.add_padding(self.username, 64).decode('hex')
        login_command += self.add_padding(self.password, 64).decode('hex')
        login_command += SESSION_ID_HEX.decode('hex')
        login_command += self.add_padding('00', 64).decode('hex')  # other valid values "01"
        return login_command
    
    def create_check_login_command(self):
        check_login_command = self.add_padding(CHECK_LOGIN_COMMAND_HEX, 4).decode('hex')
        check_login_command += MAGIC_NUMBER_STR
        check_login_command += self.add_padding('04', 4).decode('hex')
        check_login_command += SESSION_ID_HEX.decode('hex')
        return check_login_command
    
    def create_video_on_command(self):
        video_on_command = self.add_padding(VIDEO_ON_COMMAND_HEX, 4).decode('hex')
        video_on_command += MAGIC_NUMBER_STR
        video_on_command += self.add_padding('a1', 4).decode('hex')
        video_on_command += '00'.decode('hex')  # videostream (0:main, 1:sub)
        video_on_command += self.add_padding(self.username, 64).decode('hex')
        video_on_command += self.add_padding(self.password, 64).decode('hex')
        video_on_command += SESSION_ID_HEX.decode('hex')
        video_on_command += self.add_padding('00', 64).decode('hex')  # other valid values "01"
        return video_on_command
    
    def connect_to_camera(self):
        status = False
        initialization = True
        socket = socket_lib.socket(socket_lib.AF_INET, socket_lib.SOCK_STREAM)
        socket.connect((self.ip, self.port))
        socket.send(self.create_header())
        socket.send(self.create_login_command())
        socket.send(self.create_check_login_command())
        # receive 1d, c8, 64 commands
        while initialization:
            response_command, packet_length_int = self.read_response_header(socket)
            self.read_response_data(packet_length_int, socket)
            if response_command == LOGIN_CHECK_REPLAY_COMMAND_HEX:
                status = True
            if response_command == PTZ_COMMAND_HEX:
                initialization = False
        return socket, status
    
    def read_response_header(self, socket=None, print_response=False):
        # read response header
        if socket is None:
            socket = self.socket
        response_command = socket.recv(4)
        if print_response : self.print_bytes_in_hex(response_command, label='command')
        magic_number = socket.recv(4)
        if magic_number != None:
            assert magic_number == MAGIC_NUMBER_STR
        packet_length = socket.recv(4)
        if print_response : self.print_bytes_in_hex(packet_length, label='length')
        packet_length_int = self.bytes_to_int(packet_length)
        return hex(ord(response_command[0])), packet_length_int
    
    def read_response_data(self, packet_length_int, socket=None, print_response=False):
        # read response data
        if socket is None:
            socket = self.socket
        total_packet_data = ''
        read = True
        while read:
            packet_data = socket.recv(packet_length_int)
            total_packet_data += packet_data
            received_data = len(packet_data) 
            if received_data == packet_length_int:
                read = False
            else:
                packet_length_int = packet_length_int - received_data 
        if print_response : self.print_bytes_in_hex(total_packet_data, label='data')
    
    def read_and_save_video(self, socket=None, video_file_name=None):
        # TODO understand the video stream duration 
        # seems that the packet length field is not used!
        if socket is None:
            socket = self.socket
        if video_file_name == None:
            video_file_name = 'video'
        video_file_path = '{}/{}.264'.format(self.directory, video_file_name)
        if os.path.exists(video_file_path):
            os.remove(video_file_path)
        socket.send(self.create_video_on_command())
        # receive 10 command
        _, packet_length_int = self.read_response_header(socket)
        self.read_response_data(packet_length_int, socket)
        # receive 1a command
        self.read_response_header(socket)
        socket.settimeout(1.0)
        try:
            while True:
                data = socket.recv(1024)
                with open(video_file_path, 'a') as f:
                    f.write(data)
        except:
            print 'time out!'
            socket.settimeout(None) 
    
    def record_motion_detection(self, video_file_name=None):
        self.socket_record, status = self.connect_to_camera()
        if status == False:
            return
        if video_file_name == None:
            video_file_name = 'video.264'
        video_file_directory = '{}/{}'.format(self.directory, datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))
        if not os.path.exists(video_file_directory):
            os.makedirs(video_file_directory)
        video_file_path = '{}/{}.264'.format(video_file_directory, video_file_name)
        if os.path.exists(video_file_path):
            os.remove(video_file_path)
        self.socket_record.send(self.create_video_on_command())
        # receive 10 command
        _, packet_length_int = self.read_response_header(self.socket_record)
        self.read_response_data(packet_length_int, self.socket_record)
        # receive 1a command
        self.read_response_header(self.socket_record)
        for _ in range(0, 100):
            data = self.socket_record.recv(1024)
            with open(video_file_path, 'a') as f:
                f.write(data)
        self.socket_record.close
        return video_file_directory, video_file_path
    
    def add_padding(self, hex_code, bytes_to_reach):
        hex_code_bytes = len(hex_code) / 2
        if len(hex_code) % 2 != 0 or hex_code_bytes > bytes_to_reach:
            raise Exception('hexadecimal code not valid')
        for _ in range(0, bytes_to_reach - hex_code_bytes):
            hex_code += '00'
        return hex_code
    
    def bytes_to_int(self, number_bytes):
        byte_value = 1
        int_value = 0
        for byte in number_bytes:
            # ord(x) value of the byte when the argument is an 8-bit string
            byte_to_int = int (hex(ord(byte)), 16)
            if byte_to_int != 0 :
                int_value += byte_to_int * byte_value
            if byte_value == 1 :
                byte_value = 256
            else:
                byte_value = byte_value * 256
        return int_value
    
    def print_bytes_in_hex(self, bytes_string, label=None):
        if label is not None:
            print '{} : '.format(label),
        new_line = 0
        for byte in bytes_string:
            hex_value = hex(ord(byte))
            if new_line < 15:
                print hex_value,
            else:
                print hex_value
                new_line = 0
            new_line += 1
        print ''

class FoscamThread(threading.Thread):
 
    def __init__(self, foscam_client, task):
        threading.Thread.__init__(self)
        self.task = task
        self.foscam_client = foscam_client

    def run(self):
        global record
        record = False
        if self.task == 'keep-alive':
            while True:
                self.foscam_client.socket.send(self.foscam_client.create_check_login_command())
                sleep(2)
        elif self.task == 'motion detection':
            while True:
                # receive 6f
                response_command, packet_length_int = self.foscam_client.read_response_header()
                if response_command == MOTION_DETECTION_COMMAND_HEX:
                    self.foscam_client.read_response_data(packet_length_int)
                    # receive 2c
                    response_command, packet_length_int = self.foscam_client.read_response_header()
                    self.foscam_client.read_response_data(packet_length_int)
                    print 'Motion detection!'
                    record = True
                    response_command, packet_length_int = self.foscam_client.read_response_header()
                self.foscam_client.read_response_data(packet_length_int)
        elif self.task == 'record':
            while True:
                if record == True:
                    video_file_name = 'motion'
                    video_file_directory, video_file_path = self.foscam_client.record_motion_detection(video_file_name=video_file_name)
                    record = False
                    # command = [settings.FFMPEG_PATH , '-i' , video_file_path , '-f' , 'image2pipe' , '-pix_fmt' , 'rgb24' , '-vcodec' , 'rawvideo' , '- ']
                    command = '{} -i {} -f image2pipe  -pix_fmt  rgb24 -vcodec  rawvideo  - '.format(settings.FFMPEG_PATH, video_file_path)
                    devnull = open(os.devnull, 'wb')
                    pipe = sp.Popen(command, shell=True, stdout=sp.PIPE, stderr=devnull)
                    try:
                        for index in range(0, 23):
                            # read 1289*730*3 bytes (= 1 frame)
                            raw_image = pipe.stdout.read(1280 * 720 * 3)
                            # transform the byte read into a numpy array
                            image = numpy.fromstring(raw_image, dtype='uint8')
                            image = image.reshape((720, 1280, 3))
                            pil_image = Image.fromarray(image)
                            pil_image.save("{}/frame_{}.jpeg".format(video_file_directory, index))
                    except Exception:
                        pass
                    # throw away the data in the pipe's buffer.
                    pipe.stdout.flush()
                    pipe.kill()