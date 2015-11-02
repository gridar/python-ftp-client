# -*- coding: utf-8 -*-
import  logging,  os,  time
from optparse import OptionParser
from optparse import OptionGroup
from ftplib import FTP
import ftplib

# display the result in the log if the result has some values
def displayLog(result,  log,  msg):
    if len(result):
        log.debug(msg + " %r ",  result)

# retrieve the files and the directories from the path given
def getElements(directory,  recursive):
    elements = {}
    for f in os.listdir(directory):
        pathFile = os.path.join(directory,f)
        if os.path.isfile(pathFile):
            elements["(File) "+directory+"/"+f] = [f,  os.stat(pathFile)]
        elif os.path.isdir(pathFile):
            elements["(Directory) "+directory+"/"+f] = [f,  os.stat(pathFile)]
            if recursive=="True":
                elements.update(getElements(directory + "/"+ f,  recursive))
    return elements

# normalizing the path of the file or the directory 
def normalizePath(path):
    element = path.replace('(File) ',  '')
    element = element.replace('(Directory) ',  '')
    element = os.path.normpath(element)
    return element
    
# add the elements (added in the local directory) to the FTP server
def addElementsToFTP(ftp,  elementsAdded,  options,  rootLogger):
      if len(elementsAdded) > 0:
            # adding the file to the ftp server
            for elementAdded in elementsAdded:
                element = normalizePath(elementAdded)
                basename = os.path.basename(element)
                dirname = os.path.dirname(element.replace(options.local_directory,  ''))
                ftp.cwd(dirname)
                elementInDir = ftp.nlst()
                # check if the element is not already added
                if str(basename )not in elementInDir:
                    if os.path.isfile(element):
                        file = open(element, 'rb')
                        ftp.storbinary('STOR '+basename,  file)
                        file.close()
                        displayLog(elementAdded,  rootLogger,  'File added to FTP server :')
                    elif os.path.isdir(element):
                        ftp.mkd(basename)
                        displayLog(elementAdded,  rootLogger,  'Directory added to FTP server :')

# remove a directory and all his content
def removeDirectory(ftp,  directory,  rootLogger):
    try:
        ftp.cwd(directory)
        elementInDir = ftp.nlst()
        for e in elementInDir:
                # go deeper in the directory
                removeDirectory(ftp,  e,  rootLogger)
        # removing the parent directory
        ftp.cwd('../')
        ftp.rmd(directory)
        displayLog(directory,  rootLogger,  'Directory removed from FTP:')
    except ftplib.error_perm as detail:
        # removing the file
        ftp.delete(directory)
        displayLog(str(detail),  rootLogger,  'File removed from FTP:')

# remove the elements (removed from the local directory) from the FTP server
def removeElementsFromFTP(ftp,  elementsRemoved,  options,  rootLogger):
      if len(elementsRemoved) > 0:
            ftp = FTP(options.ftp_host)
            ftp.login(options.ftp_login,  options.ftp_password)
            # deleting the file from the ftp server
            for elementAdded in elementsRemoved:
                is_file = '(File)' in elementAdded
                is_directory = '(Directory)' in elementAdded
                element = normalizePath(elementAdded)
                basename = os.path.basename(element)
                dirname = os.path.dirname(element.replace(options.local_directory,  ''))
                # check if the element has not been already removed
                try:
                    ftp.cwd(dirname)
                    if is_file:
                        displayLog(ftp.delete(basename),  rootLogger,  'Using ftp.delete()...')
                        displayLog(elementAdded,  rootLogger,  'File deleted from FTP server :')
                    elif is_directory:
                        removeDirectory(ftp,  basename,  rootLogger)
                except ftplib.error_perm as detail:
                    displayLog(str(detail),  rootLogger,  'Element already removed or not found: ')

def spyDirectory(options,  rootLogger):
        # retrieving the elements to be compared
        elementsBefore = getElements(options.local_directory,  options.include_subdir)
        
        while True:
            elementsAdded = []
            elementsRemoved = []
            elementsAltered = []
            
            time.sleep (float(options.refresh_delay)/1000.0)
            
            # retrieving the new elements
            elementsNext = getElements(options.local_directory,  options.include_subdir)
            
            # retrieving the elements added and altered
            for k,  v in elementsNext.items():
                if k not in elementsBefore:
                    elementsAdded.append(k)
                elif  elementsNext[k][1] != elementsBefore[k][1]:
                    elementsAltered.append(k)
            
            # retrieving the elements removed
            for k,  v in elementsBefore.items():
                if k not in elementsNext:
                    elementsRemoved.append(k)
            
            # setting the elements previously retrieved by the new elements
            elementsBefore = elementsNext
            
            # logging the result
            displayLog(elementsAdded,  rootLogger,  "Elements added :")
            displayLog(elementsRemoved,  rootLogger,  "Elements removed :")
            displayLog(elementsAltered,  rootLogger,  "Elements altered :")
            
            # initializing the conneciton with the FTP sever
            ftp = FTP(options.ftp_host)
            ftp.login(options.ftp_login,  options.ftp_password)
            ftp.cwd(options.ftp_directory)
            
            # adding, updating and reomving elements from FTP server
            addElementsToFTP(ftp,  elementsAdded,  options,  rootLogger)
            removeElementsFromFTP(ftp,  elementsRemoved,  options,  rootLogger)
            
            # closing the connection with the FTP server
            ftp.quit()

def main():
     # setting the logger to log in the console with the WARNING level (by default)
    rootLogger = logging.getLogger()
    logFormatter = logging.Formatter("%(asctime)s [%(levelname)-5.5s] %(message)s")
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)
    
    try:
        # defining the options
        parser = OptionParser()
        parser.add_option("-d", "--debug",  default=False)
        parser.add_option("-p", "--path_log",  default="")
        # ... for the local directory to spy
        group = OptionGroup(parser, "File monitoring options")
        group.add_option("-l", "--local_directory", help="The path of the direcotry to spy")
        group.add_option("-r", "--refresh_delay",  default=1000,  help="Refresh delay time [default]")
        group.add_option("-i", "--include_subdir",  default=False, help="Include the sub direcotry [default]")
        parser.add_option_group(group)
        # ... for the ftp server
        group = OptionGroup(parser, "FTP parameters")
        group.add_option("-H", "--ftp_host",  help="FTP host")
        group.add_option("-f", "--ftp_directory",  default="/",  help="FTP directory [default]")
        group.add_option("-o", "--ftp_login",  help="FTP login")
        group.add_option("-P", "--ftp_password",  help="FTP password")
        parser.add_option_group(group)
        
        # retrieving the parameters
        (options, args) = parser.parse_args()
           
        if not os.path.isdir(options.local_directory):
            raise Exception("Local directory not found")
            
        if options.debug== "True":
            # setting the logger to log in the file and in the console with the DEBUG level
            rootLogger.setLevel(logging.DEBUG)
            fileHandler = logging.FileHandler("{0}{1}.log".format(options.path_log, "surveillance"))
            fileHandler.setFormatter(logFormatter)
            rootLogger.addHandler(fileHandler)        
        
        # logging the parameters given by the user
        rootLogger.debug("Directory : %s",  options.local_directory)
        rootLogger.debug("Debug : %s",  options.debug)
        rootLogger.debug("Path for the log file : %s",  options.path_log)
        rootLogger.debug("Refresh delay : %s",  options.refresh_delay)
        rootLogger.debug("Include sub directory : %s",  options.include_subdir)
        
        # spying the directory 
        spyDirectory(options,  rootLogger)

    except Exception as e:
        rootLogger.error(e)

if __name__ == "__main__":
    main()
    
    
