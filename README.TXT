ArtHistory
An INFO 4302 project.
Developed by: Eric Swidler, Stephanie Gary, and Jessica Kane
Cornell University, Fall 2012

Running the Program:
To run the application on your machine, just clone the git project, navigate to the src folder, and run the command “python art_history.py”. By default, it runs on port 8888. It's dependent on urlparse, urllib, and tornado. Make sure you have those installed.


Updating the Database:
The application points to a MongoLab database. To refresh the contents of that database, navigate to the database_script folder and run the command "python painting_crawler.py". It's dependent on the SPARQLWrapper, simplejson, and httplib2. Make sure you have those installed. As a warning, the script will take between 30 minutes and a hour to run.


Changing the Page Counts file:
Changing the pagecounts file actually involves changing code. First, you need to download the new file, unzip it, and place it in the database_script folder. Then update the main method of the painting_crawler.py script to point to the name of that file (it's at line 298). 

CRUD Operations

To return all paintings: 

	localhost:8888/paintings (will redirect to html representation)
	localhost:8888/paintings.xml (other formats: .json, .ttl, .html)

To return a particular painting with id=3:

	http://localhost:8888/paintings/3
	http://localhost:8888/paintings/3.json (or .ttl, .xml, .html)
	
To add a new painting:
	
	curl -i -X POST -d '["painting",{"title":"NewTitle", "year_created":"2012", "where": "newLocation"}]' http://localhost:8888/paintings
	
	^^fill in all fields data is available for: {title, year_created, where, lat, lng, image, artist, medium, description}

To update a painting:

	curl -i -X PUT -d '["painting",{"title":"NewTitle", "year_created":"2012", "where": "newLocation"}]' http://localhost:8888/paintings/5

To delete a painting:
	
	curl -i -X DELETE http://localhost:8888/paintings/1

