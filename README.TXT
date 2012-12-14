ArtHistory
An INFO 4302 project. 

Running the Program:
To run the application on your machine, just clone the git project, navigate to the src folder, and run the command “python art_history.py”. By default, it runs on port 8888. It's dependent on urlparse, urllib, and tornado. Make sure you have those installed.


Updating the Database:
The application points to a MongoLab database. To refresh the contents of that database, navigate to the database_script folder and run the command "python painting_crawler.py". It's dependent on the SPARQLWrapper, simplejson, and httplib2. Make sure you have those installed.


Changing the Page Counts file:
Changing the pagecounts file actually involves changing code. First, you need to download the new file, unzip it, and place it in the database_script folder. Then update the main method of the painting_crawler.py script to point to the name of that file (it's at line 298). 
