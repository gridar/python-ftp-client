from ftplib import FTP

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    BLINK_GREEN = '\033[5;41;32m'
    UNDERLINE = '\033[4m'


def send_file(ftp, file_path):
  data = open(file_path, 'rb')
  ftp.storbinary('STOR ' + file_path, data)
  data.close()

def nope(arg):
  print 'noping a while'

def print_file_name(name, prefix):
  print prefix, bcolors.BOLD + bcolors.OKGREEN + name + bcolors.ENDC

def print_directory_name(name, prefix):
  print prefix, bcolors.OKBLUE + name + bcolors.ENDC

def print_all_ftp(ftp, prefix='|'):

  ftp_list = []
  ftp.retrlines('LIST',ftp_list.append)

  for ftp_object in ftp_list:
    if ftp_object[0] == 'd':
      ftp_dir_name = ftp_object.split(' ')[-1]
      ftp.cwd(ftp_dir_name)
      print_directory_name(ftp_dir_name, prefix)
      print_all_ftp(ftp, prefix = prefix + '    |' )
    else:
      ftp_file_name = ftp_object.split(' ')[-1]
      print_file_name(ftp_file_name, prefix)
  ftp.cwd('../')

ftp = FTP()
ftp.connect('127.0.0.1', '59496')
print ftp
print ftp.login()
print ftp.getwelcome()

print_all_ftp(ftp,'|')

print send_file(ftp, 'wapiti')
print ftp.quit()
