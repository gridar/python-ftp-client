# -*- coding: utf-8 -*-
import  logging,  os,  time,  ftplib
from optparse import OptionParser
from optparse import OptionGroup

# display the result in the log if the result has some values
def displayLog(result,  log,  msg):
    if len(result):
        log.debug(msg + " %r ",  result)
        
# check the options given by the user
def checkOptions(options):
    if not options.ftp_login:
        raise Exception('FTP login required')
    elif not options.ftp_password:
        raise Exception('FTP password required')
    elif not options.ftp_host:
        raise Exception('Host required')
    elif not options.local_directory:
        raise Exception('Local directory required')
    elif not os.path.isdir(options.local_directory):
        raise Exception("Local directory not found")

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

def getDirname(elementPath,  options):
    return str(os.path.normpath(options.ftp_directory + os.path.dirname(elementPath.replace(options.local_directory,  '')))).replace('\\',  '/')

# normalizing the path of the file or the directory 
def normalizePath(path):
    element = path.replace('(File) ',  '')
    element = element.replace('(Directory) ',  '')
    element = os.path.normpath(element)
    return str(element)

# add a single element to the ftp server
def addElement(ftp,  path,  basename,  rootLogger):
    file = open(path, 'rb')
    ftp.storbinary('STOR '+basename,  file)
    file.close()
    displayLog(path,  rootLogger,  'File added to FTP server :')

# add the elements (added in the local directory) to the FTP server
def addElementsToFTP(ftp,  elementsAdded,  options,  rootLogger):
    if len(elementsAdded) > 0:
        # sort the elements added in order to create the directories first
        elementsAdded.sort()
        # adding the files or directory to the ftp server
        for elementAdded in elementsAdded:
            # retrieving the path of the file or the directory
            elementPath = normalizePath(elementAdded)
            # retrieving the file name or the directory name
            basename = str(os.path.basename(elementPath))
            # retrieving the path of the current directory
            dirname = getDirname(elementPath,  options)
            try:
                displayLog(ftp.pwd(),  rootLogger,  'addElementsFTP currently in')
                displayLog(dirname + ' '+ftp.pwd(),  rootLogger,  'addElementsFTP moving to ...')
                # moving to the current dorectory
                ftp.cwd('/')
                ftp.cwd(dirname)
                elementInDir = ftp.nlst()
                # check if the element is not already added
                if str(basename) not in elementInDir:
                    if os.path.isfile(elementPath):
                        # the size of the file is reasonable, we can send it
                        addElement(ftp,  elementPath,  basename,  rootLogger)
                    elif os.path.isdir(elementPath):
                        # adding a new directory
                        ftp.mkd(basename)
                        displayLog(elementAdded,  rootLogger,  'Directory added to FTP server :')
            except ftplib.error_perm as detail:
                displayLog(str(detail) +' '+elementPath,  rootLogger,  "Element already added or it's not a directory: ")

# remove a directory and all his content
def removeDirectory(ftp,  element,  rootLogger):
    try:
        # moving to the sub directory (if element is a directory)...
        ftp.cwd(element)
        elementInDir = ftp.nlst()
        for e in elementInDir:
                # go deeper in the directory
                removeDirectory(ftp,  e,  rootLogger)
        # removing the current directory
        ftp.cwd('../')
        ftp.rmd(element)
        displayLog(element,  rootLogger,  'Directory removed from FTP:')
    except ftplib.error_perm as detail:
        # ...or removing the file (if element is a file)
        ftp.delete(element)
        displayLog(str(detail) + " it's a file : " +str(element),  rootLogger,  'File removed from FTP.')

# remove the elements (removed from the local directory) from the FTP server
def removeElementsFromFTP(ftp,  elementsRemoved,  options,  rootLogger):
      if len(elementsRemoved) > 0:
            # deleting the elements from the ftp server
            for elementRemoved in elementsRemoved:
                is_file = '(File)' in elementRemoved
                is_directory = '(Directory)' in elementRemoved
                # retrieving the path of the file or the directory
                elementPath = normalizePath(elementRemoved)
                # retrieving the file name or the directory name
                basename = str(os.path.basename(elementPath))
                # retrieving the path of the current directory
                dirname = getDirname(elementPath,  options)
                try:
                    displayLog(ftp.pwd(),  rootLogger,  'removeElementFTP currently in')
                    displayLog(dirname,  rootLogger,  'removeElementsFTP moving to ')
                    # moving to the current directory
                    ftp.cwd('/')
                    ftp.cwd(dirname)
                    # deleting the file if the element is a file
                    if is_file:
                        ftp.delete(basename)
                        displayLog(elementPath,  rootLogger,  'File deleted from FTP server :')
                    elif is_directory:
                        # deleteing the directory and all his content if the element is a directory
                        removeDirectory(ftp,  basename,  rootLogger)
                except ftplib.error_perm as detail:
                    displayLog(str(detail) + ' '+ elementPath,  rootLogger,  'Element already removed or not found: ')

# update element to the ftp server
def updateElementsFromFTP(ftp,  elementsUpdated,  options,  rootLogger):
    filesAltered = []
    for elementUpdated in elementsUpdated:
        if '(File)' in elementUpdated:
            filesAltered.append(elementUpdated)
    
    # deleting and creating the files altered
    removeElementsFromFTP(ftp,  filesAltered,  options,  rootLogger)
    addElementsToFTP(ftp,  filesAltered,  options,  rootLogger)
    
# spy a directory by detecting a file/direcotry added, removed or updated
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
            ftp = ftplib.FTP(options.ftp_host)
            ftp.login(options.ftp_login,  options.ftp_password)
            
            # adding, updating and removing elements from FTP server
            removeElementsFromFTP(ftp,  elementsRemoved,  options,  rootLogger)
            addElementsToFTP(ftp,  elementsAdded,  options,  rootLogger)
            updateElementsFromFTP(ftp,  elementsAltered,  options,  rootLogger)
            
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
        parser.add_option("-d", "--debug",  default=False,  help="Enable the debug mode [default]")
        parser.add_option("-p", "--path_log",  default="",  help="Path to log [default]")
        # ... for the local directory to spy
        group = OptionGroup(parser, "File monitoring options")
        group.add_option("-l", "--local_directory", help="The path of the directory to spy")
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
        
        # chekc the options given by the user
        checkOptions(options)
        options.ftp_diretory = os.path.normpath(options.ftp_directory)
        
        if options.debug== "True":
            # setting the logger to log in the file and in the console with the DEBUG level
            rootLogger.setLevel(logging.DEBUG)
            fileHandler = logging.FileHandler("{0}{1}.log".format(options.path_log, "ftpsynchro"))
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

# main of the program
if __name__ == "__main__":
    main()
    
    

