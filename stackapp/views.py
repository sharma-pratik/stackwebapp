import site
from urllib import request
from django.shortcuts import render
from django.views.generic import ListView
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
import json
from rest_framework.response import Response
from rest_framework import status
import datetime
import requests
import os
import json
from .throttle import *

class SessionManagement(object):

    """
    A class used for managing the session
    ...

    Attributes
    ----------
    request : request
        http request object

    Methods
    -------
    set_session(*args)
        set the user requested input filter data into the current session object

    get_previous_session_data(*args)
        check and fetches the current stored session data
    """


    def __init__(self, request : HttpRequest) -> None:
        """
        Parameters
        ----------
        request : request
            http request object
        """

        self.request = request

    def set_session(self, *args : list) -> None:
        """
        set the user requested input filter data into the current session object
        
        It will save the follwing data :
            - start_date : start time in epoch format
            - end_date : end time in epoch format
            - site_name : stackoverflow site name
            - search_text : search text
            - pages : used for pagination. Storing information for each page. It will used in case of datatable,
                      when user request for previous/next page information. It will have key (page number) which 
                      in turn contain following keys :
                        - data : list of data having question name, question link and tags values
                        - has_more : Boolean value given by Stackoverflow API representing if more data can be fetch or not

        Parameters
        ----------
        args : list
            list of user selected input filter data
        
        Return
        ------
        None
    
        """

        
        if self.request.session.get("paging_info") is None:
            self.request.session["paging_info"] = {"data" : {"start_date" : "", "end_date" : "", "site_name" : "", "search_text" : ""}, "pages" : {}}
        
        self.request.session["paging_info"]["data"]["start_date"] = args[0]
        self.request.session["paging_info"]["data"]["end_date"] = args[1]
        self.request.session["paging_info"]["data"]["site_name"] = args[2]
        self.request.session["paging_info"]["data"]["search_text"] = args[3]
        self.request.session["paging_info"]["pages"][args[4]] = {"data" : [], "has_more" : None}
        self.request.session["paging_info"]["pages"][args[4]]["data"] = args[5]
        self.request.session["paging_info"]["pages"][args[4]]["has_more"] = args[6]

    def get_previous_session_data(self, *args) -> dict or None:

        """
        Check and fetches the current stored session data
        
        It will check information submitted in request against the information stored in session.
        The checking will be based on start date, end date, site nae, search text, page number.

        Parameters
        ----------
        args : list
            list of user selected input filter data like
            - start_date : start time in epoch format
            - end_date : end time in epoch format
            - site_name : stackoverflow site name
            - search_text : search text
            - page : page number
        
        Return
        ------
        None : in case if no matching data found
        Dict : information containing question, links and tags values
        """

        
        if self.request.session.get("paging_info") and self.request.session.get("paging_info")["pages"].get(args[4]) and \
            self.request.session.get("paging_info")["data"]["start_date"] == args[0]  and \
            self.request.session.get("paging_info")["data"]["end_date"] == args[1] and \
            self.request.session.get("paging_info")["data"]["site_name"] == args[2] and \
            self.request.session.get("paging_info")["data"]["search_text"] == args[3]:
            return self.request.session.get("paging_info")["pages"].get(args[4])
        else:
          
            return None



class StackAPIView(ListView):

    """
    Configuring context data for showing datatable

    Methods
    -------
    get(request, *args, **kwargs)
        rendering the html with context data
    """

    def get(self, request: HttpRequest, *args: list, **kwargs: dict) -> HttpResponse:
        """
        Render the html with context data

        It will read the site_names.json file storing in current app in order to load the
        list of sites names given by stackoverflow and return in the render() method
        
        """
        
        # Reading json file
        json_file_path = os.path.join("stackapp","site_names.json")

        site_names = open(json_file_path, "r").read().split("\n")
        site_names.pop(-1)
        
        site_names = [ json.loads(item) for item in site_names[0:4]]
        
        return render(request, "stack.html", context={"site_names": site_names})


class ListStackQuestions(PerMinThrottle, PerHourThrottle):

    """
    Request data from stackoverflow API or from the sessions

    Methods
    -------
    get(request, *args, **kwargs)
        rendering the html with context data
    """


    def get(self, request: HttpRequest, *args: list, **kwargs: dict) -> HttpResponse:
        page_limit = 30 # page limit
        page_number = str(round(int(request.GET.get("iDisplayStart")) / 10 ) +1) # page number

        # convertion into epoch format
        start_date = str(round(datetime.datetime.strptime(request.GET.get("start_date"), "%m/%d/%Y").timestamp()))
        end_date  = str(round(datetime.datetime.strptime(request.GET.get("end_date"), "%m/%d/%Y").timestamp()))

        search_text = request.GET.get("title", "")
        site_name = request.GET.get("site_name", "")
        session_management = SessionManagement(request=request)
        data = []
        has_more = False

        # checking if data exists in session
        previous_session_info = session_management.get_previous_session_data(start_date, end_date, site_name, search_text, page_number)
        if previous_session_info:
            for item in previous_session_info["data"]:
                data.append(
                    item
                )
            has_more = previous_session_info.get("has_more")
        else:
            base_URI = "https://api.stackexchange.com/2.3"
            query_parms = "?site="+site_name+\
                      "&order=desc&sort=activity&fromdate="+str(start_date)+"&end_date="+str(end_date)+ \
                          "&page="+page_number+"&pagesize="+str(page_limit)+"&title="+search_text
            
            # quering specific question 
            if search_text:
                URI = base_URI + "/search/advanced" + query_parms
            # querying random question 
            else:
                URI = base_URI + "/questions" + query_parms
            response = requests.get(URI).json()

            if response.get("items"):
                items = response["items"]

                for item in items:
                    data.append(
                        [item["title"], ",".join(item["tags"]), item["link"]]
                    )

                has_more = response["has_more"]
                # storing info into session
                session_management.set_session(start_date, end_date, site_name, search_text, page_number, data, has_more)
                request = session_management.request
                request.session.modified = True
            else:
                return Response(
                    data=["Stackoverflow api limit exceed"],
                    status = status.HTTP_429_TOO_MANY_REQUESTS
                )

        resp = {
            "data" : data,
            "recordsTotal" : 1000 if has_more else 0,
            "recordsFiltered" : 1000 if has_more else 0
        }
        return Response(
            data=resp,
            status = status.HTTP_200_OK
        )
