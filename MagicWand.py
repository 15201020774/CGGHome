#! /usr/bin/python
import os, shutil
import sys

import re

import getopt

reportName =""
queryName ="" 
fileName ="" 
gsqlFileName = ""

def usage():
  print "\nThis is the usage function\n"
  print 'Usage: '+sys.argv[0]+' -r <ReportName> -q <QueryName> -o <ReportFile> -f <GSQLFile>'

def main(argv):
  try:
    opts, args = getopt.getopt(argv, '-help:r:q:o:f:', ['help', 'ReportName=', 'QueryName=', 'ReportFile=,' 'GSQLFile='])
    if not opts:
      print 'No options supplied'
      usage()
    #elif args != 6:
    #	usage()
    #	sys.exit(2)
    else:
    	for opt, arg in opts:
    		if opt in ('-h', '--help'):
    			usage()
    			sys.exit(2)
    		if opt in ('-r', '--ReportName'):
    			#print arg + ":reportName"
    			global reportName
    			reportName = arg
    		if opt in ('-q', '--QueryName'):
    			#print arg + ":queryName"
    			global queryName
    			queryName = arg
    		if opt in ('-o', '--ReportFile'):
    			#print arg + ":fileName"
    			global fileName
    			fileName = arg
    		if opt in ('-f', '--GSQLFile'):
    			#print arg + ":gsqlFileName"
    			global gsqlFileName
    			gsqlFileName = arg
  except getopt.GetoptError,e:
    print e
    usage()
    sys.exit(2)

if __name__ =='__main__':
    main(sys.argv[1:])

#print reportName + ":" + queryName + ":" + fileName + ":" + gsqlFileName


rsl_header    = """ADV-RSL-2.2
/*---------------------------------------------------------------------------
| Copyright (c) 2021
| Advent Software, Inc.  San Francisco, California, USA.
| All Rights Reserved.
*----------------------------------------------------------------------------
| $Source$
| $Revision$
| $Date$
| $Author$
| $State$
| Comments:
*--------------------------------------------------------------------------*/

REPORT  \"Report_Name\"
(	
#include \"acctparam.include\"
  NODEF 	Portfolio, 
	NODEF 	ScreenType,	
	DATE 	  PeriodStartDate = BeginToday,
	DATE	  PeriodEndDate = EndToday, 
	DATE	  KnowledgeDate = EndToday,
	DATE	  KnowledgeBeginDate = \"1901/01/01\", 
	DATE    PriorKnowledgeDate = EndToday,
	NODEF   AccountingPeriod,
	NODEF   AccountingCalendar,
	STRING	StyleName = \"e\",
  STRING  ManagementFirm,
	STRING	AddendumPages,
	STRING  DisableLocAcctFilters = \"Yes\",
	STRING  DisableStrategyFilters = \"Yes\",
	LIBSTRUCT LIBAccountingFiltersType AccountingFilters,
	STRING	PortfolioDescription

	)

STYLE :StyleName 
SUBMISSION SCREEN ComplexAcctRepsByInv TYPE Position,Dynamic,ClosedPeriod,Books;

RECORD DateDetail
{
  DateString, DateValue
};

RECORD Period_Dates
{
  PeriodStart, PeriodEnd
};"""

rsl_header = rsl_header.replace("Report_Name",reportName)

print_header = """
print_report_header()
{
	BEGINHEADER;
	PUSHFORMAT __Title;
  //  Company Name
	PRINT :ManagementFirm FIRM NAME;
  //  Report Name
	:PrintReportName = :__reportName;
	PRINT :PrintReportName REPORT TITLE;
  //  Portfolio Description
	PRINT :PortfolioDescription PORTFOLIO NAME;
	
// Period Start Date
	PUSHFORMAT __TitleDates;
	// For static runs, we print out the period name and period
	// start date.
	if(:AccountingRunType == "ClosedPeriod" OR :AccountingRunType == "Books")
	{
	  :td.DateString = "Accounting Period" ;
	  :td.DateValue = :PrintPeriod;
//	  PRINT :td HEADER DATE;
	:td.DateString = "Period Start Date" ;
	:td.DateValue = :PeriodStartDate;
	PRINT :td HEADER DATE;
	}

  // Period End Date
	:td.DateString = "Period End Date" ;	
	:td.DateValue = :PeriodEndDate;
	PRINT :td HEADER DATE;
  // Prior Knowledge Date
	if (:AccountingRunType != "Dynamic")
	{
          :td.DateString = "Prior Knowledge Date";
          :td.DateValue = :PriorKnowledgeDate;
          PRINT :td HEADER DATE;
	}	
  // Knowledge Date

	:td.DateString = "Knowledge Date" ;
	:td.DateValue = :KnowledgeDate;
	PRINT :td HEADER DATE;

  // Accounting Calendar
	if (:AccountingCalendar != "")
	{
          :td.DateString = "Accounting Calendar";
	  :td.DateValue = :AccountingCalendar;
	  PRINT :td HEADER DATE;
	}
  // Accounting Period
	if (:AccountingPeriod != "")
	{
          :td.DateString = "Accounting Period";
          :td.DateValue = :AccountingPeriod;
          PRINT :td HEADER DATE;
	}
	POPFORMAT;
  

  // AccountingFilters
	PUSHFORMAT __TitleDates;
        if (:AccountingFilters.InvObjectList != "")
	{
          :td.DateString = :AccountingFilters.InvObjectType || " "  || :AccountingFilters.InvFilterType || "d" ;
	  :td.DateValue = :AccountingFilters.InvObjectList;
	  PRINT :td HEADER DATE;
	}

	POPFORMAT;
	
	PUSHFORMAT Data;
	PRINTHEADINGS;
	ENDHEADER;
}
"""   

main_str="""
MAIN
{
  print_report_header();\n
"""

fieldVar_str = "FIELD field_name\t\t\t\t\t\"field_name\"\t\t20  JUST = LEFT, XTYPE = STRING;"
fieldVar_date = "FIELD field_name\t\t\t\t\t\"field_name\"\t\t30	JUST = LEFT, DATEFORMAT = \"MM/DD/YYYY:HH24:MI:SS\", XTYPE = Date;"
fieldVar_qty = "FIELD field_name\t\t\t\t\t\"field_name\"\t\t20	JUST = RIGHT, PREC = ::__qPrec, XTYPE = DECIMAL;"
fieldVar_price = "FIELD field_name\t\t\t\t\t\"field_name\"\t\t20	JUST = RIGHT, PREC = ::__pPrec, XTYPE = DECIMAL;"
fieldVar_money = "FIELD field_name\t\t\t\t\t\"field_name\"\t\t20	JUST = RIGHT, PREC = ::__mPrec, XTYPE = DECIMAL;"

rrformatVar = "RRFORMAT Data"


print "\n****************************Start to Generate RSL from GSQL *************\n"

# read gsql
file1 = open(gsqlFileName, 'r')
Lines = file1.readlines()


def parenthetic_contents(string):
    """Generate parenthesized contents in string as pairs ( contents)."""
    stack = []
    for i, c in enumerate(string):
        if c == '(':
            stack.append(i)
        elif c == ')' and stack:
            start = stack.pop()
            if len(stack) == 0 :
            #yield (len(stack),string[start + 1: i])
            	yield (string[start + 1: i])


with open(gsqlFileName, 'r') as file:
    data = file.read().replace('\n', '')
    temp = data.find("FROM")
    #print str(temp) + "ddddd"
    newData= data[:temp]
    #print newData

for x in list(parenthetic_contents(newData)) :
	#print x
	newData = newData.replace(x, 'AAAA', 1)
	#print newData
	
#print "**********************************************\n"
#print "newData:" + newData

#sys.exit()

print "Read the alias..\n"
aliases = newData.split(",")
aliasesNew = []
for alias in aliases :
	alias=alias.rstrip()	
	index = alias.rfind(' ')
	length = len(alias)
	#print alias + ":" +str(index) + alias[index:length-1]
	aliasesNew.append(alias[index+1:length])
		
print aliasesNew
print "\nBegin to write a new RSL..\n"
file1 = open(fileName, "w")  
file1.writelines(rsl_header)
file1.writelines("\n")
file1.writelines("\n")

#record
print "Add record..\n"
file1.writelines("Record Info")
file1.writelines("{")

count = len(aliasesNew)
i=0
for alias in aliasesNew:
	i+=1
	if i == count:
		file1.writelines(alias)
	else:
		file1.writelines(alias + ",")
		file1.writelines("\n")
file1.writelines("};")
file1.writelines("\n")

# vairable
file1.writelines("\n\nVARIABLE Info rb;")
file1.writelines("\nVARIABLE PrintReportName;")
file1.writelines("\nVARIABLE DateDetail td;")
file1.writelines("\nVARIABLE Period_Dates periodDates;")
file1.writelines("\nVARIABLE longFirmName, longBookCurr, LS, PrintPeriod;\n")

#Field
print "Add Field..\n"
for alias in aliasesNew:
	if "Mkt" in alias :
		tempField = fieldVar_money.replace("field_name", alias)
		file1.writelines(tempField)
		file1.writelines("\n")
	if "Amount" in alias :
		tempField = fieldVar_money.replace("field_name", alias)
		file1.writelines(tempField)
		file1.writelines("\n")
	elif "Price" in alias:
		tempField = fieldVar_price.replace("field_name", alias)
		file1.writelines(tempField)
		file1.writelines("\n")
	elif "Date" in alias:
		tempField = fieldVar_date.replace("field_name", alias)
		file1.writelines(tempField)
		file1.writelines("\n")
	else:
		tempField = fieldVar_str.replace("field_name", alias)
		file1.writelines(tempField)
		file1.writelines("\n")

file1.writelines("\n")

#RRFormat
print "Add RRFORMAT..\n"
file1.writelines(rrformatVar)
file1.writelines("\n")
count = len(aliasesNew)
i=0
for alias in aliasesNew:
	i+=1
	if i == count:
		file1.writelines(alias)
	else:
		file1.writelines(alias + ",\t\t\t\tSpace 2,\n")
file1.writelines(";")
file1.writelines("\n")

#query
print "Add QUERY..\n"
file1.writelines("\nQUERY ")
file1.writelines(queryName)
file1.writelines("\n")
file1.writelines(Lines)
if Lines[len(Lines) - 1].endswith(";") == False:
	file1.writelines(";")
#file1.writelines(";")
file1.writelines("\n")

#print_header
file1.writelines("\n")
file1.writelines(print_header);
file1.writelines("\n")

#body
print "Add body..\n"
file1.writelines("\n\n\nbody()\n{\n");
file1.writelines("print :rb;\n")
file1.writelines("}\n")
file1.writelines("\n")
file1.writelines("\n")

#main
print "Main..\n"
file1.writelines(main_str);
file1.writelines("\nGET ")
file1.writelines(queryName)
file1.writelines(" INTO :rb EXECUTING body;\n")
file1.writelines("\n")
file1.writelines("}")

file1.close() 
print "Done."



