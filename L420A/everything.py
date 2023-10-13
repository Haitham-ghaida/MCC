import premise as ps
import bw2io as bi
import bw2data as bd
import bw2calc as bc
import uuid
import pandas as pd
import sys
from Simulation.sim_BM import *

def setup():

    bd.projects.set_current('MCCFF')

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
        
        
    ndb = ps.NewDatabase(
        scenarios=[
            {"model":"image", "pathway":"SSP2-Base", "year":2020},
            {"model":"image", "pathway":"SSP2-Base", "year":2030},
            {"model":"image", "pathway":"SSP2-Base", "year":2040},
            {"model":"image", "pathway":"SSP2-Base", "year":2050},
            {"model":"image", "pathway":"SSP2-Base", "year":2060},
            {"model":"image", "pathway":"SSP2-Base", "year":2070},
            {"model":"image", "pathway":"SSP2-Base", "year":2080},
            # {"model":"image", "pathway":"SSP2-RCP26", "year":2020},
            # {"model":"image", "pathway":"SSP2-RCP26", "year":2030},
            # {"model":"image", "pathway":"SSP2-RCP26", "year":2040},
            # {"model":"image", "pathway":"SSP2-RCP26", "year":2050},
            # {"model":"image", "pathway":"SSP2-RCP26", "year":2060},
            # {"model":"image", "pathway":"SSP2-RCP26", "year":2070},
            # {"model":"image", "pathway":"SSP2-RCP26", "year":2080},
        ],
        source_db="ecoinvent-3.9.1-cuttoff", # <-- name of the database in the BW2 project. Must be a string.
        source_version="3.9.1", # <-- version of ecoinvent. Can be "3.5", "3.6", "3.7" or "3.8". Must be a string.
        key='tUePmX_S5B8ieZkkM7WUU2CnO8SmShwmAeWK9x2rTFo=', # <-- decryption key
        # to be requested from the library maintainers if you want ot use default scenarios included in `premise`
        use_multiprocessing=True # <-- set to True if you want to use multiprocessing
    )

    ndb.update_all()
    # ndb.write_db_to_brightway(["SSP2-Base_2020", "SSP2-Base_2030", "SSP2-Base_2040", "SSP2-Base_2050", "SSP2-Base_2060", "SSP2-Base_2070", "SSP2-Base_2080", "SSP2-RCP26_2020", "SSP2-RCP26_2030", "SSP2-RCP26_2040", "SSP2-RCP26_2050", "SSP2-RCP26_2060", "SSP2-RCP26_2070", "SSP2-RCP26_2080"])
    ndb.write_db_to_brightway(["SSP2-Base_2020", "SSP2-Base_2030", "SSP2-Base_2040", "SSP2-Base_2050", "SSP2-Base_2060", "SSP2-Base_2070", "SSP2-Base_2080",])


def constructor_main(file, sheet):
    building_data_construction = pd.read_excel(io = file, sheet_name = sheet, engine = 'openpyxl')
    for index in building_data_construction.index :
        Product(name=building_data_construction['Ecoinvent_activity_construction'][index],
                id=building_data_construction['ID'][index],
                amount = building_data_construction['Amount'][index],
                unit = building_data_construction['Unit'][index],
                service_life = building_data_construction['Service_life'][index],
                production_lci = building_data_construction['Ecoinvent_key_construction'][index],
                eol_lci = building_data_construction['Ecoinvent_key_eol'][index]
            )

def renovation_main(file, sheet):
    building_data_renovation = pd.read_excel(io = file, sheet_name = sheet, engine = 'openpyxl')
    for index in building_data_renovation.index :
        Product(name=building_data_renovation['Ecoinvent_activity_renovation'][index],
                id=building_data_renovation['ID'][index],
                amount = building_data_renovation['Amount'][index],
                unit = building_data_renovation['Unit'][index],
                service_life = building_data_renovation['Service_life_renovation'][index],
                production_lci = building_data_renovation['Ecoinvent_key_renovation'][index],
                eol_lci = building_data_renovation['Ecoinvent_key_renovation_eol'][index],
                major_renovation_possible = True,
                renovation_product = True
            )
        # check if there is a match in id between renovation and construction products and if yes then set major renovation possible to true
        for product in Product.real_instances:
            if product.id == building_data_renovation['ID'][index]:
                product.major_renovation_possible = True

class Product:
    '''This class represents a product in the system, it should take care of the following:
    - Create a unique id for each product
    - Create a unique serial number for each product
    - Keep track of the product's service life
    '''
    # keep track of all instances of the class
    real_instances = []
    all_instances = []
    renovation_instances = []
    def __init__(self, name: str, id: int, amount: float, unit: str, service_life: int = None, production_lci: str = None, eol_lci: tuple[str,str] = None,
                major_renovation_possible : bool = False, renovation_product = False):
        # randomly generated id
        self.random_id = uuid.uuid4().hex
        self.id = id
        self.name = name
        self.amount = amount
        self.unit = unit
        self.production_lci = production_lci
        self.service_life = service_life
        self.eol_lci = eol_lci
        self.embodied_impacts = {}
        self.major_renovation_possible = major_renovation_possible
        self.renovation_product = renovation_product
        # only append if not renovation product
        if not self.renovation_product:
            self.real_instances.append(self)
        else:
            self.renovation_instances.append(self)
        self.all_instances.append(self)

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
        
    
    def add_renovation_points(self, product: Product):
        '''
        This function adds points to the time line where replacements occur'''
        first_repl = product.service_life + self.start
    
        
        # here is for replacements
        for i in range(first_repl, self.end-1, product.service_life):
            if product.major_renovation_possible:
                for p in Product.renovation_instances:
                    if p.id == product.id:
                        self.points.append((i, p))
            else:
                self.points.append((i, product))
        self.points = list(set(self.points))
        # sort by year
        self.points = sorted(self.points, key=lambda x: x[0])
        return self.points
    
    def add_eol_points(self, product: Product):
        '''This function adds points to the time line where eol occurs'''
        if product.major_renovation_possible:
            for p in Product.renovation_instances:
                if p.id == product.id:
                    self.points.append((self.end, p))
        else:
            self.points.append((self.end, product))
            
        
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
            
    
    def match_renovation_product(self, product):
        '''This function matches the renovation product with the construction product'''
        for p in Product.real_instances:
            if p.id == product.id:
                return p

    
    def clean_list_renovation(self):
        clean_list = []
        check_if_first_time = []
        
        for point in self.points:
            if not point[1].renovation_product:
                clean_list.append((point[0], point[1].production_lci, point[1]))
                clean_list.append((point[0], point[1].eol_lci, point[1]))
                
        # now lets add the production and eol activities of the products that are renovation possible
        for point in self.points:
            if point[1].renovation_product and point[1] not in check_if_first_time:
                clean_list.append((point[0], point[1].production_lci, point[1]))
                clean_list.append((point[0], self.match_renovation_product(point[1]).eol_lci, self.match_renovation_product(point[1])))
                # add the renovation product to the check list
                check_if_first_time.append(point[1])
                
            elif point[1].renovation_product and point[1] in check_if_first_time:
                clean_list.append((point[0], point[1].production_lci, point[1]))
                clean_list.append((point[0], point[1].eol_lci, point[1]))
        return clean_list
    
    def clean_list_eol(self):
        clean_list = []
        for point in self.points:
            if point[0] == self.end:
                clean_list.append((point[0], point[1].eol_lci, point[1]))
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
                 methods: list[tuple[str,str,str]] = [('EF v3.0 EN15804', 'climate change', 'global warming potential (GWP100)'),],
                 yearly_databases: dict = None,
                 products: list[Product] = None,):
        self.activities_and_years = activities_and_years
        self.methods = methods
        self.yearly_databases = yearly_databases
        self.results = {}
        self.results_aggregated = {}
        self.products = products
        
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
        for year, activity, _ in self.activities_and_years:            
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
 
    def production_lca(self, db = 'ecoinvent-3.9.1-cuttoff', mfa_start = 2020):
        results_dict = {}
         
        for p, product in enumerate(self.products):            
            # Construct a unique key for storing results
            result_key = (mfa_start, product, db)    
        
            # Ensure this returns the expected activity
            try:
               activity = bd.get_activity((str(db), product.production_lci))
            except:
                print(f'something wrong with {product.production_lci}')
                sys.exit(1)
               
           
            # Define the functional unit for the LCA
            amount = product.amount
            fu = {activity: amount}
           
            #  if p==0:
                # Initialize the LCA with the first method and calculate impacts
            lca = bc.LCA(fu, self.methods[0])
            lca.lci()
            lca.lcia()
            #  else:
            #     lca.redo_lcia(fu)
           
             # Initialize a list to store impact scores for all methods
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
    
    def give_me_operational(self, mfa_start = 2020, mfa_end = 2080, climate = french_climate, metadata = french_metadata, heating_set_point = 18 ):
        '''
        give me the operational LCA of the building, considering the energy consumption
        Returns:

        '''
        # initialize an empty dictionary to store results
        results_dict = {}
        # Localisation of possible renovations
        reno_dict = {'231 Bearing outer wall':None,
             '251 Loadbering deck':None,
             '262 Roof covering':None,
             '234 Windows':None,
             '291 Mass inventory heating':None}
        service_life_outer_wall = 38
        service_life_floor = 35
        service_life_roof = 35
        service_life_windows = 30
        service_life_heating_system = 26
        dates_new_energetic_simulations = [mfa_start, 
                                           mfa_start + service_life_heating_system,
                                           mfa_start + service_life_windows,
                                           mfa_start + service_life_roof,
                                           mfa_start + service_life_outer_wall,
                                           mfa_end]
        
        energy_consumption = 0
        operational_lca = 0
        # iterate through all the years where the energy simulation will change
        for i in range (1, len(dates_new_energetic_simulations)) :
            year_duration = dates_new_energetic_simulations[i] - dates_new_energetic_simulations[i-1]
            print(year_duration)
            year = dates_new_energetic_simulations[i]
            old_year = dates_new_energetic_simulations[i-1]
            if i==1 :
                reno_dict['291 Mass inventory heating'] = 1
            if i==2 :
                reno_dict['234 Windows'] = 1
            if i==3 :
                reno_dict['262 Roof covering'] = 1
                reno_dict['51 Loadbering deck'] = 1
            if i==4 :
                reno_dict['231 Bearing outer wall'] = 1
            energy_consumption = FMES(climate, metadata, reno_dict) * year_duration
            dbs = self.database_chooser(year)      
            for db in dbs:
                
            # Choose the appropriate activity : energy consumption
            
            # Before the renovation of the heating system : gas boiler so energy consumption all in gas
                if i==1 :
                    demand = bd.get_activity((str(db), '6a60dc6386928f379bff65ad8c801001'))
                    amount = energy_consumption * 10.6
                else : # energy consumption all in electricity thanks to heat pump
                    demand = bd.get_activity((str(db), '35e0230404c1d9c808244206d6747650'))
                    amount = energy_consumption
                    print(energy_consumption)
                
                result_key = (year, demand, db)
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
                results_dict[result_key] = impacts
        return results_dict
                
     


def bd_get_activity(db_code) -> str:
        bd.projects.set_current('MCC')
        return bd.get_activity(db_code)['name']
    
class GiveMeName:
    
    '''
    an abstract class that takes care of the following:
    - writing the results to excel
    -aggregating the results
    - TO BE DONE: aggregating the results based on the time line'''
    
    # def aggregator_renovation(lcia_dict, product) -> dict:
    #     # find all the keys in the lcia dictionary that contain the product code
    #     keys = [key for key in lcia_dict.keys() if product.production_lci in key or product.eol_lci in key]
    #     print(keys)

    #     # Create a new dictionary that contains only the relevant keys
    #     aggregated_lcia = {key: [x * product.amount for x in lcia_dict[key]] for key in keys}
        
    #     return aggregated_lcia
    
    def aggregator_renovation_eol(lcia_dict, product, list) -> dict:
        pass
        
    

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
        activity_codes = set()

        for product_data in data.values():
            for (year, activity_code, database) in product_data.keys():
                activity_codes.add(activity_code)
                    
        activity_names = {code: bd_get_activity(('ecoinvent-3.9.1-cuttoff', code)) for code in activity_codes}
        dfs = {}
        print(data)

        for product_name, impacts_data in data.items():
            for (year, activity_code, database), impacts in impacts_data.items():
                for impact_idx, impact in enumerate(impacts):
                    if impact_idx not in dfs:
                        dfs[impact_idx] = []

                    dfs[impact_idx].append({
                        'Year': year,
                        'Database': database,
                        'Activity': activity_names[activity_code],
                        'Product': product_name,
                        'Impact': impact
                    })

        dfs = {key: pd.DataFrame(value).set_index(['Year', 'Database', 'Activity', 'Product']) for key, value in dfs.items()}

        for key, df in dfs.items():
            dfs[key] = df.sort_index(level='Year')

        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            for sheet, df in dfs.items():
                df.to_excel(writer, sheet_name=f'Impact_{sheet}')


