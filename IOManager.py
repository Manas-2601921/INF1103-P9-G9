from datetime import datetime
import managers
class IOManager:
    

    def __init__(self):
        self.__incident_name = None
        self.__incident_description = None
        self.__incident_datetime = None
        self.__location = None
        self.__reporter_role = None
        self.__injury_reported = None
        self.__immediate_action = None

    @property
    def incident_name(self):
        return self.__incident_name

    @property
    def incident_description(self):
        return self.__incident_description

    @property
    def incident_datetime(self):
        return self.__incident_datetime

    @property
    def location(self):
        return self.__location

    @property
    def reporter_role(self):
        return self.__reporter_role

    @property
    def injury_reported(self):
        return self.__injury_reported

    @property
    def immediate_action(self):
        return self.__immediate_action
    
    def prompt_incident_name(self):
        while True:
            newIncidentName = input("Enter the name of the incident (or type 'quit' to exit): ")
            if newIncidentName.lower() == 'quit':
                return "quit"
            if not newIncidentName.strip():
                print("Incident name cannot be empty. Please give the incident a short title.")
                continue
            return newIncidentName

    def prompt_incident_description(self):
        while True:
            newIncidentDescription = input("Enter the description of the incident (or type 'quit' to exit): ")
            if newIncidentDescription.lower() == 'quit':
                return "quit"
            if not newIncidentDescription.strip():
                print("Description cannot be empty. Please describe what happened.")
                continue
            return newIncidentDescription

    def prompt_incident_datetime(self):
        while True:
            newIncidentDateTime = input("Enter the date and time of the incident (DD-MM-YYYY HH:MM) (or type 'quit' to exit):")
            if newIncidentDateTime.lower() == 'quit':
                return "quit"
            elif newIncidentDateTime is None:
                print("Invalid input. Please enter a valid incident date and time.")
                continue
            else:
                try:
                    newIncidentDateTime = datetime.strptime(newIncidentDateTime, "%d-%m-%Y %H:%M")
                    return newIncidentDateTime
                except ValueError:
                    print("Invalid date and time format. Please enter the date and time in the format DD-MM-YYYY HH:MM.")
                    continue

    def prompt_incident_location(self):
        while True:
            newIncidentLocation = input(f"Enter the location of the incident (or type 'quit' to exit): " + "\nFor example: Warehouse, Office, Factory, etc.")
    
            if newIncidentLocation.lower() == 'quit':
                return "quit"
            if not newIncidentLocation.strip():
                print("Location cannot be empty. Please enter where the incident happened.")
                continue
            return newIncidentLocation

    # Constants for the different roles that can report an incident. The keys are the input values that the user can enter, and the values are the corresponding role names.
    ROLE_OPTIONS = {
        "1": "Employee", "employee": "Employee",
        "2": "Supervisor", "supervisor": "Supervisor",
        "3": "Manager", "manager": "Manager",
        "4": "Client", "client": "Client"
    }

    def prompt_reporter_role(self):
        print("\nSelect your role in the company:")
        print("  1. Employee")
        print("  2. Supervisor")
        print("  3. Manager")
        print("  4. Client")
    
        while True:
            answer = input("Enter the option number or role name (or type 'quit' to exit): ").strip()
    
            if answer.lower() == 'quit':
                return "quit"
    
            role = self.ROLE_OPTIONS.get(answer.lower())
            if role:
                return role
    
            print("Invalid input. Please enter a valid role.")

    def prompt_injury_reported(self):
        while True:
            newIncidentInjuryReported = input("Was there any injury reported Y/N (or type 'quit' to exit): ")
            if newIncidentInjuryReported.lower() == 'quit':
                return "quit"
            elif newIncidentInjuryReported.upper() == 'Y' or newIncidentInjuryReported.upper() == 'YES':
                newIncidentInjuryReported = True
                return newIncidentInjuryReported
            elif newIncidentInjuryReported.upper() == 'N' or newIncidentInjuryReported.upper() == 'NO':
                newIncidentInjuryReported = False
                return newIncidentInjuryReported
            else:
                print("Invalid input. Please enter 'Y' for Yes or 'N' for No.")
                continue

    def prompt_immediate_action(self):
        while True:
            immediateAction = input("Was there any immediate action taken Y/N (or type 'quit' to exit): ")
            if immediateAction.lower() == 'quit':
                return "quit"
            elif immediateAction.upper() == 'Y' or immediateAction.upper() == 'YES':
                while True:
                    newImmediateAction = input("Please describe the immediate action taken: ")
                    if newImmediateAction.strip():
                        return newImmediateAction
                    print("Description cannot be empty. Please describe the action taken.")
            elif immediateAction.upper() == 'N' or immediateAction.upper() == 'NO':
                immediateAction = "No immediate action was taken"
                return immediateAction
            else:
                print("Invalid input. Please enter 'Y' for Yes or 'N' for No.")
                continue

    # function to collect all the incident details from the user and store them in the class attributes. If the user types "quit" at any point, the function will return False to indicate that the process was aborted.
    def collect_incident_details(self):
        
        self.__incident_name = self.prompt_incident_name()
        if self.__incident_name == "quit":
            return False

        self.__incident_description = self.prompt_incident_description()
        if self.__incident_description == "quit":
            return False

        self.__location = self.prompt_incident_location()
        if self.__location == "quit":
            return False

        self.__reporter_role = self.prompt_reporter_role()
        if self.__reporter_role == "quit":
            return False

        self.__incident_datetime = self.prompt_incident_datetime()
        if self.__incident_datetime == "quit":
            return False

        self.__injury_reported = self.prompt_injury_reported()
        if self.__injury_reported == "quit":
            return False

        self.__immediate_action = self.prompt_immediate_action()
        if self.__immediate_action == "quit":
            return False

        return True

    # To be added into main.py

    # # Collect all incident information
    # if managers.io_manager.collect_incident_details():

    #     print("\nIncident information collected successfully!")

    #     print(managers.io_manager.incident_name)
    #     print(managers.io_manager.incident_description)
    #     print(managers.io_manager.location)
    #     print(managers.io_manager.reporter_role)
    #     print(managers.io_manager.incident_datetime)
    #     print(managers.io_manager.injury_reported)
    #     print(managers.io_manager.immediate_action)

    # else:
    #     print("Incident reporting cancelled.")

    
    @staticmethod
    def display_search_options():
        while True:
            search_option = input("What would you like to search by:\n1. Incident Name \n2. Category\n3. Date \nEnter your option number here (or type 'quit' to exit): ").strip()
            if search_option.lower() == "quit":
                return "quit"
            if search_option.isdigit():
                search_option_int = int(search_option)
                if search_option_int in [1,2,3]:
                    return search_option_int
                else:
                    print("Error: invalid option number. Please enter the option number 1-3 or quit.")
            else:
                print("Error: invalid option number. Please enter the option number 1-3 or quit.")

    def handle_search_option(self,search_option:int):
        if(search_option == 1):
            while True:
                input_incident_name = input("Enter the name of the incident you want to search for (or type 'quit' to exit): ").strip()
                input_incident_name_lower = input_incident_name.lower()
                if input_incident_name_lower == "quit":
                    return "quit"
                elif input_incident_name_lower == "":
                    print("Error: Incident name cannot be empty.")
                elif input_incident_name_lower:
                    break

            incidents_by_name_records = self.find_by_title(input_incident_name_lower)
            if(incidents_by_name_records):
                return incidents_by_name_records,input_incident_name
            return [], input_incident_name

                
        elif(search_option == 2):
            incident_categories = self.get_all_incident_categories()
            if incident_categories:
                print("\nCategories related to all your incidents:")
                for incident_category in incident_categories:
                    print(f"  - {incident_category}")
                while True:
                    input_incident_category = input("Enter the category of the incident you want to search for (or type 'quit' to exit):").strip()
                    input_incident_category_lower = input_incident_category.lower()
                    if input_incident_category_lower == "quit":
                        return "quit"
                    elif input_incident_category_lower in incident_categories:
                        break
                    else:
                        print("Error: Invalid search category. Please re-enter")
                incidents_by_category_records= self.find_by_category(input_incident_category_lower)
                if incidents_by_category_records:
                    return incidents_by_category_records,input_incident_category
                return [], input_incident_category
            else:
                print("Error: No categories to search by. Please search by the other options.")
                return "quit"
        elif(search_option == 3):
            while True:
                input_datetime_search_type = input("Search incident datetime by \n1. Date and Time Range\n2. Specific Datetime\nEnter your option number here (or type 'quit' to exit):").strip()
                if input_datetime_search_type.lower() == "quit":
                    return "quit"
                if(input_datetime_search_type == "1"):
                    while True:
                        input_start_datetime = input("Enter the start datetime (DD-MM-YYYY HH:MM) (or type 'quit' to exit): ")
                        if input_start_datetime.lower() == "quit":
                            return "quit"
                        elif not self.is_valid_dt_format(input_start_datetime):
                            print("Error: Invalid format. Please follow the format: DD-MM-YYYY HH:MM (e.g., 25-10-2023 14:30)")
                        elif self.is_valid_dt_format(input_start_datetime):
                            break
                    while True:
                        input_end_datetime = input("Enter the end datetime (DD-MM-YYYY HH:MM) (or type 'quit' to exit): ")
                        if input_end_datetime.lower() == "quit":
                            return "quit"
                        elif not self.is_valid_dt_format(input_end_datetime):
                            print("Error: Invalid format. Please follow the format: DD-MM-YYYY HH:MM (e.g., 25-10-2023 14:30)")
                        elif self.is_valid_dt_format(input_end_datetime):
                            break
                    iso_start_dt = datetime.strptime(input_start_datetime, "%d-%m-%Y %H:%M").isoformat(timespec="seconds")
                    iso_end_dt = datetime.strptime(input_end_datetime, "%d-%m-%Y %H:%M").isoformat(timespec="seconds")
                    if iso_start_dt > iso_end_dt:
                        print("End datetime cannot be earlier than the start datetime. Please try again.")
                    else:
                        incidents_by_datetime_records = self.find_by_datetime_range(iso_start_dt, iso_end_dt)
                        return incidents_by_datetime_records, f"search results between {input_start_datetime} and {input_end_datetime}"
                elif(input_datetime_search_type == "2"):
                    while True:
                        input_specific_datetime = input("Enter the specific datetime (DD-MM-YYYY HH:MM) (or type 'quit' to exit): ")
                        if input_specific_datetime.lower() == "quit":
                            return "quit"
                        elif not self.is_valid_dt_format(input_specific_datetime):
                            print("Error: Invalid format. Please follow the format: DD-MM-YYYY HH:MM (e.g., 25-10-2023 14:30)")
                        elif self.is_valid_dt_format(input_specific_datetime):
                            try:
                                iso_specific_dt = datetime.strptime(input_specific_datetime, "%d-%m-%Y %H:%M").isoformat(timespec="seconds")
                            except ValueError:
                                print("Error: Invalid datetime format. Please make sure datetime field is valid datetime format")
                                continue
                            incidents_by_datetime_records = self.find_by_specific_datetime(iso_specific_dt)
                            return incidents_by_datetime_records, input_specific_datetime
                else:
                    print("Error: Invalid datetime search option entered. Please enter only options 1 or 2")
        else:
            print("Error: Invalid search option entered. Please enter only options 1, 2, or 3")

 
    def display_search_results(self, search_results_data, user_search_query):
        num_of_search_results = len(search_results_data)
        if num_of_search_results == 0:
            print(f"No Search Results for '{user_search_query}'\n")
            return "quit"

        print(f"\n{num_of_search_results} incident(s) for '{user_search_query}':\n")
        for i, data in enumerate(search_results_data, start=1):
            formatted_datetime = datetime.fromisoformat(data['input']['incident_datetime']).strftime("%d %B %Y, %H:%M")
            print(f"[{i}] {data['input']['incident_name']}")
            print(f"{'Incident Date and Time':<22}: {formatted_datetime}")
            print(f"{'Location':<22}: {data['input']['location']}")
            print("-" * 47, "\n")

        while True:
            search_result_input = input("Enter the search result number to view incident details (or type 'quit' to exit): ").strip()

            if search_result_input.lower() == "quit":
                return "quit"
            try:
                view_incident_number = int(search_result_input)
                if view_incident_number < 1 or view_incident_number > num_of_search_results:
                    print(f"Error: please enter a number thats shown in the search results (or type 'quit' to exit).")
                    continue
                elif 1 <= view_incident_number <= num_of_search_results:
                    incident_display = search_results_data[view_incident_number - 1]
                    print(self.format_incident_record(incident_display) + "\n")
                    break
            except ValueError:
                print("Error: invalid search result number. Please enter a whole number from the search results(or type 'quit' to exit).")
                continue
            break

    def format_incident_record(self, incident_record: dict) -> str:
        # shortcuts so the lines below stay readable
        details = incident_record['input']
        ai = incident_record['ai']
        logic = incident_record['logic']

        formatted_datetime = datetime.fromisoformat(details['incident_datetime']).strftime("%d %B %Y, %H:%M")

        # width that every label is padded to in the sections below
        LABEL_WIDTH = 24

        lines = []

        # report header
        lines.append("=" * 20)
        lines.append("Incident Report")
        lines.append("=" * 20)
        lines.append("")

        # section 1: the details the person originally submitted
        lines.append("Incident details")
        lines.append("-" * 20)
        lines.append(f"{'Incident Name:':<{LABEL_WIDTH}}{details['incident_name']}")
        lines.append(f"{'Incident Description:':<{LABEL_WIDTH}}{details['description']}")
        lines.append(f"{'Incident DateTime:':<{LABEL_WIDTH}}{formatted_datetime}")
        lines.append(f"{'Incident Location:':<{LABEL_WIDTH}}{details['location']}")
        # converts the True/False value into "Yes"/"No" for readability
        lines.append(f"{'Injury Reported:':<{LABEL_WIDTH}}{'Yes' if details['injury_reported'] else 'No'}")
        lines.append(f"{'Immediate Action:':<{LABEL_WIDTH}}{details['immediate_action']}")

        # section 2: what the AI concluded about the incident, plus which review queue it ended up in
        lines.append("")
        lines.append("Our Assessment")
        lines.append("-" * 20)
        lines.append(f"{'Severity':<{LABEL_WIDTH}}{ai['severity']}")
        lines.append(f"{'Incident Type':<{LABEL_WIDTH}}{ai['incident_type']}")
        lines.append(f"{'Explanation':<{LABEL_WIDTH}}{ai['severity_explanation']}")
        lines.append(f"{'Review Status':<{LABEL_WIDTH}}{logic['final_queue']}")

        # section 3: only the risk indicators the AI flagged as True
        lines.append("")
        lines.append("Risk Indicators")
        lines.append("-" * 20)
        for indicator, is_flagged in ai['indicators'].items():
            if is_flagged:
                # make names readable, e.g. "fire_hazard" becomes "fire hazard"
                lines.append(indicator.replace("_", " "))

        # section 4: the AI's suggested next step
        lines.append("")
        lines.append("Recommended Immediate Action")
        lines.append("-" * 20)
        # ">" is used as the marker
        lines.append(f"> {ai['recommended_immediate_action']}")

        return "\n".join(lines)
        
    @staticmethod
    def find_by_title(incident_title:str):
        results = managers.data_manager.query(
            lambda record: (record.get("input", {}).get("incident_name") or "").strip().lower() == incident_title.strip().lower()
        )
        if results != None or []:
            return results
        else:
            return []

    @staticmethod
    def find_by_category(incident_category:str):
        results = managers.data_manager.query(
            lambda record: (record.get("ai", {}).get("hazard_category") or "").strip().lower() == incident_category.strip().lower()
        )
        if results != None or []:
            return results
        else:
            return []

    @staticmethod
    def get_all_incident_categories():
        incident_categories = sorted({
            (record.get("ai", {}).get("hazard_category") or "").strip()
                for record in managers.data_manager.query(lambda record: True)
                if (record.get("ai", {}).get("hazard_category") or "").strip()
        })
        if(incident_categories):
            return incident_categories
        else:
            return False
    @staticmethod
    def find_by_datetime_range(start_datetime:datetime, end_datetime:datetime):
        search_results = managers.data_manager.query(
            lambda record: start_datetime <= (record.get("input", {}).get("incident_datetime") or "") <= end_datetime
        )
        if not search_results:
            return []
        return search_results 

    @staticmethod
    def find_by_specific_datetime(specific_datetime:datetime):
        search_results = managers.data_manager.query(
            lambda record: record.get("input", {}).get("incident_datetime") == specific_datetime
        )
        if not search_results:
            return []
        else:
            return search_results 
    @staticmethod
    def is_valid_dt_format(value_to_check):
        format="%d-%m-%Y %H:%M"
        try:
            datetime.strptime(value_to_check, format)
            return True
        except ValueError:
            return False

    FLASH_CATEGORIES = ("error", "success", "info")

    def notify(self, message: str, category: str = "error") -> None:
        """Display a flow-level message via Flask flash (or stdout in CLI).

        Imports Flask lazily inside the method so ``IOManager`` stays
        importable without the web stack installed or active.
        """
        level = category if category in self.FLASH_CATEGORIES else "info"
        try:
            from flask import flash, has_request_context
        except ImportError:
            print(message)
            return

        if has_request_context():
            flash(message, level)
        else:
            print(message)
