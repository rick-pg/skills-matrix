import argparse
import httplib2
import time
import json
import os
import re
import subprocess
import sys

sys.path.append('.')

from apiclient import discovery
from collections import defaultdict

try:
    from oauth2client import client
    from oauth2client import tools
    from oauth2client.file import Storage
except ImportError:
    print("[Error] Update OAuth with: pip install --upgrade google-api-python-client")
    exit(0)


SCOPES = 'https://www.googleapis.com/auth/spreadsheets.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Sheets API Python Quickstart'


def run_command(command):
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    if p.stderr:
        for err in iter(p.stderr.readline, b''):
            print err
    return iter(p.stdout.readline, b'')


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME

        # run_flow needs parsed arguments but we don't want it to choke on the sync-all param
        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            parents=[tools.argparser])
        flags = parser.parse_args()

        credentials = tools.run_flow(flow, store, flags)
        print('Storing credentials to ' + credential_path)
    return credentials


def get_matrix_contents():
    """Uses Sheets API to download the list of stories that QA wants copied from prod to dev

    Creates a Sheets API service object to read the document and return the stories.  See:
    https://developers.google.com/sheets/quickstart/python for the sample code this is based on
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')

    # Silence stderr for GAE memcache temporarily (spurious, noisy error for this operation)
    null_fd = os.open(os.devnull, os.O_RDWR)
    save = os.dup(2)
    os.dup2(null_fd, 2)

    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)

    spreadsheetId = '14lyNCcKWORmZ-jd8Dd8HO8jX-858evEbUjh0nCJ7hKE'
    rangeName = 'Full Matrix!A1:T30'
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheetId, range=rangeName).execute()

    # Restore stderr
    os.dup2(save, 2)
    os.close(null_fd)
    values = result.get('values', [])

    # Map the contents into dictionaries
    discipline = []
    for col in values[1]:
        discipline.append(col)

    category = {}
    cat = None
    for i in range(len(discipline)):
        if i < len(values[0]) and values[0][i]:
            cat = values[0][i].split()[0].lower()
        category[discipline[i]] = cat

    skills = defaultdict(list)
    for row in values[2:]:
        for i in range(len(row)):
            if row[i]:
                skills[discipline[i]].append(row[i])

    return discipline, category, skills


discipline, category, skills = get_matrix_contents()
index_file = open('matrix/index.html', 'w')
print >>index_file, """
<html>
<head>
    <title>Engineering Skills Matrix</title>

    <style type="text/css">
    body {
    	font-family: Helvetica, sans-serif;
    }
    h1 {
    	width: 90%;
    	margin: 20px auto !important;
    	text-align: left;
    }
    h1 img {
    	vertical-align: baseline;
    	float: right;
    }
    #content {
    	border: 1px solid #999;
    	margin: 20px auto 4px;
    	overflow: auto;
    	width: 90%;
    }
    #disciplineNav {
    	width: 25%;
    	margin: 0;
    	float: left;
    	list-style: none;
    }
    #disciplineNav li {
    	background-color: #ddd;
    	border: 1px inset #fff;
    	padding: 4px;
    }
    #disciplineNav li.active {
    	border: 1px outset #fff;
	}
    #disciplineNav li.active span {
    	text-shadow: 1px 1px #aaa;
	}
    #disciplineNav li.craft {
    	background-color: #b6d7a8;
	}
    #disciplineNav li.team {
    	background-color: #a2c4c9;
	}
    #disciplineNav li.results {
    	background-color: #a4c2f4;
	}
    #disciplineNav li:hover i {
    	text-shadow: 1px 1px #aaa;
    }
    i.icon-pushpin {
    	display: inline-block;
    	padding: 0 4px;
    	color: transparent;
    }
    i.icon-pushpin.pinned {
    	color: #333;
    }
    #detailsView {
    	margin: 16px 0 16px 60px;
    	width: 55%;
    	float: left;
    }
    #detailsView li {
    	padding: 2px;
    }
    h2 {
    	margin-top: 0;
    }
    h2.craft {
    	border-bottom: 1px solid #b6d7a8;
    }
    h2.team {
    	border-bottom: 1px solid #a2c4c9;
    }
    h2.results {
    	border-bottom: 1px solid #a4c2f4;
    }
    #generated {
    	width: 90%;
    	margin: 0 auto;
    	font-size: 11px;
    }
    </style>
	<link href="https://netdna.bootstrapcdn.com/twitter-bootstrap/2.3.2/css/bootstrap-combined.no-icons.min.css" rel="stylesheet">
	<link href="https://netdna.bootstrapcdn.com/font-awesome/3.2.1/css/font-awesome.css" rel="stylesheet">

</head>
<body ng-app="MatrixViewerApp" ng-controller="matrixViewerController">
<h1>
	<img src="http://pocketgems.com/wp-content/themes/pocket-gems/images/pg-new-logo.png"/>
	Engineering Skills Matrix
</h1>
<div id="content">
	<ul id="disciplineNav">
	    <li ng-repeat="discipline in disciplines | orderBy:sortKey" ng-class="[categories[discipline], {active: discipline == curDisc}]" ng-click="setDiscipline(discipline)">
	    	<i ng-class="[icon-pushpin, {pinned: pinned[discipline]}]" class="icon-pushpin" ng-click="togglePin(discipline)"></i>
	    	<span>{{ discipline }}</span>
	    </li>
	</ul>
	<div id="detailsView">
	    <h2 class="{{ categories[curDisc] }}">{{ curDisc }}</h1>

	    <Ul>
	    	<li ng-repeat="skill in skills[curDisc]">{{ skill }}</li>
	    </ul>
	</div>
</div>
<div id="generated">
	Last updated: {{ timestamp }}
</div>
<script>
"""

print >>index_file, "var disciplines = %s;" % json.dumps(discipline)
print >>index_file, "var categories = %s;" % json.dumps(category)
print >>index_file, "var skills = %s;" % json.dumps(skills)
print >>index_file, "var timestamp = '%s'" % time.strftime('%X %x %Z')

print >>index_file, """
</script>
<script src="https://ajax.googleapis.com/ajax/libs/jquery/2.1.1/jquery.min.js"></script>
<script src="https://ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular.min.js"></script>
<script>
angular.module('MatrixViewerApp', [
  'MatrixViewerApp.controllers'
]);

angular.module('MatrixViewerApp.controllers', []).
controller('matrixViewerController', function($scope) {
    $scope.disciplines = disciplines;
    $scope.categories = categories;
    $scope.skills = skills;
    $scope.timestamp = timestamp;
    $scope.curDisc = disciplines[0];

    $scope.pinned = {};
    for (var i = 0; i < disciplines.length; i++) {
      $scope.pinned[disciplines[i]] = false;
    }
    // Restore saved pins
    if (location.hash) {
      var pinned = location.hash.substring(1).split(',');
      for (var i = 0; i < pinned.length; i++) {
        $scope.pinned[$scope.disciplines[parseInt(pinned[i])]] = true;
      }
    }

    $scope.setDiscipline = function(discipline) {
      $scope.curDisc = discipline;
    }

    $scope.togglePin = function(discipline) {
      $scope.pinned[discipline] = !$scope.pinned[discipline];
      // Save pin in hash
      var pinIndex = $scope.disciplines.indexOf(discipline);
      var strIndex = pinIndex < 10 ? '0' + pinIndex : '' + pinIndex;
      var hash = location.hash;
      if ($scope.pinned[discipline]) { // Pinned, add it
        hash += (hash) ? ',' + strIndex : '#' + strIndex;
      } else { // Unpinned
        hash = hash.replace(',' + strIndex, '');
        hash = hash.replace(strIndex + ',', '');
        hash = hash.replace('#' + strIndex, '');
      }
      location.hash = hash;
    }

    $scope.sortKey = function(discipline) {
      var index = $scope.disciplines.indexOf(discipline);
      return ($scope.pinned[discipline] ? 'a ' : 'b ') + (index < 10 ? '0' + index : index);
    }
});
</script>
</body>
</html>
"""
index_file.close()

# Check the diff to see if we should commit the new file
command = 'git diff --stat'.split()
for line in run_command(command):
    match = re.search('\s+matrix/index.html\s+\|\s+(\d+)', line)
    if match:
        if int(match.group(1)) > 2:
            print "content changed... committing updates"
            os.system("git add matrix/index.html")
            os.system("git commit -m \"content update on %s\"" % time.strftime('%X %x %Z'))
            os.system("git push origin master")
        else:
            print "no content update to commit: %s" % line

