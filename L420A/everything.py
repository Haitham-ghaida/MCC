import premise as ps
import bw2io as bi
import bw2data as bd
import bw2calc as bc
import uuid
import pandas as pd

def setup():

    bd.projects.set_current('MCC')

    bi.bw2setup()

    ei391cdir = "/home/haithamth/Documents/ecoinvent/ecoin_cuttoff_391/ecoinvent 3.9.1_cutoff_ecoSpold02/datasets"
    data_base_name = "ecoinvent-3.9.1-cuttoff"
    if data_base_name in bd.databases:
        print("Database has already been imported")
    else:
        ei391c = bi.SingleOutputEcospold2Importer(ei391cdir, data_base_name)
        ei391c.apply_strategies()
        ei391c.statistics()

        #ei39.drop_unlinked(True)
        ei391c.write_database()
        
        
    # ndb = ps.NewDatabase(
    #     scenarios=[
    #         {"model":"image", "pathway":"SSP2-RCP19", "year":2020},
    #         {"model":"image", "pathway":"SSP2-RCP26", "year":2020},
    #         {"model":"image", "pathway":"SSP2-RCP19", "year":2030},
    #         {"model":"image", "pathway":"SSP2-RCP26", "year":2030},
    #         {"model":"image", "pathway":"SSP2-RCP19", "year":2040},
    #         {"model":"image", "pathway":"SSP2-RCP26", "year":2040},
    #     ],
    #     source_db="ecoinvent-3.9.1-cuttoff", # <-- name of the database in the BW2 project. Must be a string.
    #     source_version="3.9.1", # <-- version of ecoinvent. Can be "3.5", "3.6", "3.7" or "3.8". Must be a string.
    #     key='tUePmX_S5B8ieZkkM7WUU2CnO8SmShwmAeWK9x2rTFo=', # <-- decryption key
    #     # to be requested from the library maintainers if you want ot use default scenarios included in `premise`
    #     use_multiprocessing=True # <-- set to True if you want to use multiprocessing
    # )

    # ndb.update_electricity()
    # ndb.write_db_to_brightway(["SSP2-RCP19_2020","SSP2-RCP26_2020", "SSP2-RCP19_2030","SSP2-RCP26_2030", "SSP2-RCP19_2040","SSP2-RCP26_2040"])
    

def constructor(file, sheet):
    building_data_construction = pd.read_excel(io = file, sheet_name = sheet, engine = 'openpyxl')
    for index in building_data_construction.index :
        Product(name=building_data_construction['Ecoinvent_activity_construction'][index],
                amount = building_data_construction['Amount'][index],
                unit = building_data_construction['Unit'][index],
                service_life = building_data_construction['Service_life'][index],
                production_lci = building_data_construction['Ecoinvent_key_construction'][index],
                eol_lci = building_data_construction['Ecoinvent_key_eol'][index]
            )
    return Product.instances

class Product:
    '''This class represents a product in the system, it should take care of the following:
    - Create a unique id for each product
    - Create a unique serial number for each product
    - Keep track of the product's service life
    '''
    # keep track of all instances of the class
    instances = []
    def __init__(self, name: str, amount: float | int, unit: str, service_life: int = None, production_lci: str = None, eol_lci: tuple[str,str] = None):
        # randomly generated id
        self.random_id = uuid.uuid4().hex
        self.name = name
        self.amount = amount
        self.unit = unit
        self.production_lci = production_lci
        self.service_life = service_life
        self.eol_lci = eol_lci
        self.embodied_impacts = {}
        self.instances.append(self) # keep track of all instances of the class

    # better representation of the class for humans
    def __repr__(self):
        return f"{self.name}"
    
    def replacement_sn(self):
        ...
        

class Mfa:
    '''
    This class represents a material flow analysis, it should take care of the following:
    - Create a time line for the analysis
    - Create a list of points in time where replacements occur
    '''
    def __init__(self, start: int = 2020, end: int = 2080, time_step: int = 10):
        self.start = start
        self.end = end
        self.time_step = time_step
        self.time_line = list(range(self.start, self.end+1, self.time_step)) # create a time line
        self.points = []
        self.embodied_impacts = {} # not currently used
        self.max_year = self.get_max_db_year()
        
    
    def add_points(self, product: Product):
        '''
        This function adds points to the time line where replacements occur'''
        first_repl = product.service_life + self.start
        
        for i in range(first_repl, self.end-1, product.service_life):
            self.points.append((i, product))
        # clean duplicates
        self.points = list(set(self.points))
        # sort by year
        self.points = sorted(self.points, key=lambda x: x[0])
        return self.points
    
    
    def create_time_line_dict(self):
        '''
        This function creates a dictionary of databases for each year in the time line'''
        # initialize a dictionary to store yearly databases
        yearly_databases = {}
        # iterate through all years in the time line
        for year in self.time_line:
            # initialize an empty list for each year
            yearly_databases[year] = []
        # iterate through all databases in the project
        for db in bd.databases:
            # split the database name by underscore ***IMPORTANT*** pay attention the the naming convention of the databases it has to be SPPX-RPCxx_YYYY
            db_processed = str(db).split("_")
            if db_processed[0] == 'ecoinvent-3.9.1-cuttoff':
                ecoinvent = db
            # if the database name has more than one element after splitting by underscore, then it is a scenario database
            elif len(db_processed) > 1:
                yearly_databases[int(db_processed[1])].append(db)
        return yearly_databases
    
    
    def get_max_db_year(self):
        '''This gives you the last(max) year in the dictionary where databases exist'''
        db_dict =  self.create_time_line_dict()
        for year in reversed(sorted(db_dict.keys())):
            if len(db_dict[year]) > 0:
                return year
            
    def clean_list_for_lca(self):
        '''this function provides the a list of tuples, the first value of the tuple is the year and the second value is the code of the activity'''
        # initialize an empty list
        clean_list = []
        for point in self.points:
            clean_list.append((point[0], point[1].production_lci))
            clean_list.append((point[0], point[1].eol_lci))
        return clean_list
    
class ProLCA:
    '''
    This class should take care of the following:
    - Create a production lca for each product
    - Create a time line based lca for each product
    - Create a future lca for each product
    - Create a future lca for the whole system
    '''
    def __init__(self, activities_and_years: list[tuple[str, int]],
                 methods: list[tuple[str,str,str]] = [('EF v3.0 EN15804', 'climate change', 'global warming potential (GWP100)'),], yearly_databases: dict = None):
        self.activities_and_years = activities_and_years
        self.methods = methods
        self.yearly_databases = yearly_databases
        self.results = {}
        self.results_aggregated = {}
        
    def database_chooser(self, year):
        '''
        This function chooses the appropriate database(s) based on the year'''
        available_years = self.yearly_databases.keys()
        # make sure that the function that create_time_line_dict is called before this function and a dictionary of yearly databases is created
        assert len(available_years) > 0, "Please create a dictionary of yearly databases first"
        # check if the year is in the available years
        if year in available_years:
            # just return the database for that year
            return self.yearly_databases[year]
        # if the year is not in the available years, then check if it is less than the minimum year
        elif year < min(available_years):
            return self.yearly_databases[min(available_years)]
        # if the year is not in the available years, then check if it is greater than the maximum year
        elif year > max(available_years):
            return self.yearly_databases[max(available_years)]
        else:
            # round down to the nearest year
            return self.yearly_databases[year - (year % 10)]

    def give_me_embodied(self):
        '''give me the lca please'''
        # initialize an empty dictionary to store results
        results_dict = {}
        # iterate through all years in the time line
        for year, activity in self.activities_and_years:            
            # Choose the appropriate database(s) based on the year
            dbs = self.database_chooser(year)
            # Iterate through all chosen databases
            for db in dbs:
                # check if year and activity are already in the results dictionary if so, skip
                if (year, activity, db) in results_dict.keys():
                    continue
                # Construct a unique key for storing results
                result_key = (year, activity, db)
                # get the activity from the database
                print(db, activity)
                demand = bd.get_activity((str(db), activity))
                # Define the functional unit for the LCA
                amount = 1
                fu = {demand: amount}
                # Initialize the LCA with the first method and calculate impacts
                lca = bc.LCA(fu, self.methods[0])
                lca.lci()
                lca.lcia()
                impacts = [lca.score]
                # If there are additional methods, switch methods and calculate additional impacts
                if len(self.methods) > 1:    
                    for method in self.methods[1:]:
                        lca.switch_method(method)
                        lca.lcia()
                        impacts.append(lca.score)

                # Store all calculated impacts in the results dictionary
                results_dict[result_key] = impacts
        return results_dict

def bd_get_activity(db_code) -> str:
        # Your existing bd.get_activity logic
        return bd.get_activity(db_code)['name']
class GiveMeName:
    
    '''
    an abstract class that takes care of the following:
    - writing the results to excel
    -aggregating the results
    - TO BE DONE: aggregating the results based on the time line'''
    
    def aggregator(lcia_dict, product) -> dict:
        # find all the keys in the lcia dictionary that contain the product code
        keys = [key for key in lcia_dict.keys() if product.production_lci in key or product.eol_lci in key]
        print(keys)

        # Create a new dictionary that contains only the relevant keys
        aggregated_lcia = {key: [x * product.amount for x in lcia_dict[key]] for key in keys}
        
        return aggregated_lcia
    

    
    import pandas as pd

    def poop_to_excel(data, output_file='output.xlsx') -> None:
        """
        Generate an Excel file containing impacts data for each product.
        
        Parameters:
            data (dict): Dictionary containing products and their respective embodied impacts data.
            bd_get_activity (function): Function to retrieve activity name based on its code.
            output_file (str): Name of the output Excel file.
            
        Returns:
            None. Writes an Excel file to the specified output path.
        """
        # Accumulating unique activity codes to reduce API/database calls
        # print('data values: ', data.values())
        # activity_codes = set([key[1] for product_data in data.values() for impacts_data in product_data.values() if isinstance(impacts_data, dict) for key in impacts_data.keys()])
        # print(activity_codes)
        activity_codes = set()

        for year_data in data.values():
            for product_data in year_data:
                activity_codes.add(product_data[1])
        print(activity_codes)
                
        activity_names = {code: bd_get_activity(('SSP2-RCP19_2030', code)) for code in activity_codes}
        dfs = {}

        # Looping through each product and its associated embodied impacts
        for year, products_data in data.items():
            for product_name, impacts_data in products_data.items():
                for (year, activity_code, database), impacts in impacts_data.items():
                    for impact_idx, impact in enumerate(impacts):
                        if impact_idx not in dfs:
                            dfs[impact_idx] = []

                        dfs[impact_idx].append({
                            'Year': year,
                            'Database': database,
                            'Activity': activity_names[activity_code],
                            'Product': product_name,  # This will now correctly use the product name
                            'Impact': impact
                        })
        # Convert data to multi-indexed DataFrames
        dfs = {key: pd.DataFrame(value).set_index(['Year', 'Database', 'Activity', 'Product']) for key, value in dfs.items()}

        for key, df in dfs.items():
            # Sort by Year in other words combine all databases for each year
            dfs[key] = df.sort_index(level='Year')

        # Exporting the data to Excel
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            for sheet, df in dfs.items():
                df.to_excel(writer, sheet_name=f'Impact_{sheet}')
