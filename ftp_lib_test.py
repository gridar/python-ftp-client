from ftplib import FTP



def send_file(ftp, file_path):
  data = open(file_path, 'rb')
  ftp.storbinary('STOR ' + file_path, data)
  data.close()

ftp = FTP()
ftp.connect('127.0.0.1', '59496')
print ftp
print ftp.login()
print ftp.getwelcome()

print ftp.retrlines('LIST')
print ftp.pwd()
print ftp.cwd('hellos')
print ftp.pwd()
print ftp.retrlines('LIST')

print send_file(ftp, 'wapiti')
print ftp.quit()
