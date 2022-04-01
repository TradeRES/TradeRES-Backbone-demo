from enum import IntEnum, unique
import sys
from spinedb_api import DatabaseMapping, DiffDatabaseMapping, export_data, import_data


@unique
class P(IntEnum):
    CLASS = 0
    OBJECT = 1
    NAME = 2
    X = 3
    ALTERNATIVE = 4


in_url = sys.argv[1]
out_url = sys.argv[2]
in_db = DatabaseMapping(in_url)
out_db = DiffDatabaseMapping(out_url)

link_relationship_class_cn = "commodity__node"

parameters_gnu = {"apparent_power": "unitSizeMVA", "capacity": "capacity", 
                  "capacity_value": "availabilityCapacityMargin", "conversion_coefficient": "conversionCoeff",
                  "fom_cost": "fomCosts", "inertia": "inertia",
                  "investment_cost": "invCosts", "ramp_limit": "maxRampDown",
                  "subunit_capacity": "unitSize", "vom_cost": "vomCosts",
                  "shutdown_cost": "shutdownCost", "start_cost": "startCostCold"}
parameters_gnu2 = {"ramp_limit": "maxRampUp"}
source_relationship_class_gnu = "node__unit__io"
link_relationship_class_gnu = "commodity__node"
target_relationship_class_gnu = "grid__node__unit__io"

parameters_u = {"annuity": "annuity"} 
source_object_class_u = "unit" 
link_relationship_class_u = "node__unit__io"
link_relationship_class2_u = "commodity__node" 
target_relationship_class_u = "grid__node__unit__io"

parameters_fn = {"capacity_factor": "capacityFactor"}
source_object_class_fn = "flow"
link_relationship_class_fn = "flow__unit"
link_relationship_class2_fn = "node__unit__io"
target_relationship_class_fn = "flow__node"

parameters_gnn = {"annuity": "annuity", "investment_cost": "invCost", 
                  "investment_limit": "transferCapInvLimit"}
source_relationship_class_gnn = "node__node"
link_relationship_class_gnn = "commodity__node"
target_relationship_class_gnn = "grid__node__node"

parameters_gnn_dir = {"availability": "availability", "capacity": "transferCap", 
                  "diffusion_coefficient": "diffCoeff", "loss": "transferLoss",
                  "vom_cost": "variableTransCost"}
source_relationship_class_gnn_dir = "node__node__direction"

parameters_gnnr = {"capability": "capability"}
source_relationship_class_gnnr = "node__node__direction__reserve_type__up_down"
target_relationship_class_gnnr = "grid__node__node__restype"

parameters_gr_min = {"reserve_reactivation_time": "reserve_reactivation_time"}
parameters_gr_max = {"gate_closure": "gate_closure", "reserve_activation_duration": "reserve_activation_duration",
                     "update_frequency": "update_frequency"}
source_relationship_class_gr = "group__reserve_type__up_down"
target_relationship_class_gr = "group__restype"

parameters_gnur_min = {"reliability": "reserveReliability"}
parameters_gnur_max = {"reserve_increase_ratio": "reserve_increase_ratio"}
parameters_gnur = {"capability": "capability"}
source_relationship_class_gnur = "node__unit__reserve_type__up_down"
target_relationship_class_gnur = "grid__node__unit__restype"


    
def add_parameter_dimension(parameters, source_relationship_class, link_relationship_class, target_relationship_class):
    subquery = in_db.wide_relationship_class_sq
    class_row = in_db.query(subquery).filter(subquery.c.name == link_relationship_class).first()
    subquery = in_db.wide_relationship_sq

    # Create a dictionary that links the new dimension to one of the old dimensions
    target_objects = {}
    for relationship_row in in_db.query(subquery).filter(subquery.c.class_id == class_row.id):
        target, source = relationship_row.object_name_list.split(",")
        target_objects[source] = target

    # Entities
    data = export_data(in_db)

    # Add the entities from the source class to a list
    x_to_move = []
    for value in data["relationships"]:
        if value[P.CLASS] == source_relationship_class:
            x_to_move.append(value[P.OBJECT])

    # Extend the dimensions of the entities and add to a list 
    moved_values = []
    for object1, object2, object3 in x_to_move:
        object_add = target_objects[object1]
        moved_values.append((target_relationship_class, (object_add, object1, object2, object3)))
        
    data.setdefault("relationships", []).extend(moved_values)
    import_data(out_db, **data)

    # Parameter values
    data = export_data(in_db)

    # Add the parameter values from the source class to a list
    x_to_move = []
    for value in data["relationship_parameter_values"]:
        if value[P.CLASS] == source_relationship_class and value[P.NAME] in parameters:           
            x_to_move.append((value[P.OBJECT], parameters[value[P.NAME]], value[P.X], value[P.ALTERNATIVE]))

    # Add the previous parameter values to a list with the extended relationship dimensions
    moved_values = []
    for (object1, object2, object3), new_parameter, x, alternative in x_to_move:
        object_add = target_objects[object1]
        moved_values.append((target_relationship_class, (object_add, object1, object2, object3), new_parameter, x, alternative))

    data.setdefault("relationship_parameter_values", []).extend(moved_values)
    import_data(out_db, **data)
  
def add_parameter_dimension_2links(parameters, source_object_class, link_relationship_class, link_relationship_class2, target_relationship_class):
    subquery = in_db.wide_relationship_class_sq
    class_row = in_db.query(subquery).filter(subquery.c.name == link_relationship_class).first()
    subquery = in_db.wide_relationship_sq

    # Create a dictionary that links a temporary dimension to the old dimension
    target_objects_temp = {}
    for relationship_row in in_db.query(subquery).filter(subquery.c.class_id == class_row.id):
        target, source = relationship_row.object_name_list.split(",") #flow, unit
        target_objects_temp[source] = target #target_objects_temp[unit] = flow
        
    subquery = in_db.wide_relationship_class_sq
    class_row = in_db.query(subquery).filter(subquery.c.name == link_relationship_class2).first()
    subquery = in_db.wide_relationship_sq

    # Create a dictionary that links the new dimension to the old dimension
    target_objects = {}
    for relationship_row in in_db.query(subquery).filter(subquery.c.class_id == class_row.id):
        target, source, dummy = relationship_row.object_name_list.split(",") #node, unit
        if source in target_objects_temp:
            target_objects[target_objects_temp[source]] = target #target_objects[flow] = node

    # Entities
    data = export_data(in_db)

    # Add the entities from the source class to a list
    x_to_move = []
    for value in data["objects"]:
        if value[P.CLASS] == source_object_class:
            x_to_move.append(value[P.OBJECT])

    # Extend the dimensions of the entities and add to a list 
    moved_values = []
    for object1 in x_to_move:
        object_add = target_objects[object1]
        moved_values.append((target_relationship_class, (object1, object_add)))

    data.setdefault("relationships", []).extend(moved_values)
    import_data(out_db, **data)

    # Parameter values
    data = export_data(in_db)

    # Add the parameter values from the source class to a list
    x_to_move = []
    for value in data["object_parameter_values"]:
        if value[P.CLASS] == source_object_class and value[P.NAME] in parameters:           
            x_to_move.append((value[P.OBJECT], parameters[value[P.NAME]], value[P.X], value[P.ALTERNATIVE]))

    # Add the previous parameter values to a list with the extended relationship dimensions 
    moved_values = []
    for object1, new_parameter, x, alternative in x_to_move:
        object_add = target_objects[object1]
        moved_values.append((target_relationship_class, (object1, object_add), new_parameter, x, alternative))

    data.setdefault("relationship_parameter_values", []).extend(moved_values)
    import_data(out_db, **data)
    
def add_parameter_dimension_2links_v2(parameters, source_object_class, link_relationship_class, link_relationship_class2, target_relationship_class):
    subquery = in_db.wide_relationship_class_sq
    class_row = in_db.query(subquery).filter(subquery.c.name == link_relationship_class).first()
    subquery = in_db.wide_relationship_sq

    # Create a dictionary that links a temporary dimension to the old dimension
    target_temp = {}
    for relationship_row in in_db.query(subquery).filter(subquery.c.class_id == class_row.id):
        target1, source, target2 = relationship_row.object_name_list.split(",") #node, unit, io
        if source not in target_temp:
            target_temp[source] = list()
        target_temp[source].extend([(target1, target2)]) #target_temp[unit] = [..., (node, io)]
        
    subquery = in_db.wide_relationship_class_sq
    class_row = in_db.query(subquery).filter(subquery.c.name == link_relationship_class2).first()
    subquery = in_db.wide_relationship_sq

    # Create a dictionary that links the new dimension to the old dimension
    target_temp2 = {}
    for relationship_row in in_db.query(subquery).filter(subquery.c.class_id == class_row.id):
        target, source = relationship_row.object_name_list.split(",") #commodity, node
        target_temp2[source] = target #target_temp2[node] = commodity
        
    target_final = {}
    for source in target_temp:
        if source not in target_final:
            target_final[source] = list()           
        list_of_items = target_temp[source]
     
        for target1, target2 in list_of_items:
            target3 = target_temp2[target1]
            target_final[source].extend([(target3, target1, target2)]) #target_final[unit] = [..., (commodity, node, io)]

    # Entities
    data = export_data(in_db)

    # Add the entities from the source class to a list
    x_to_move = []
    for value in data["objects"]:
        if value[P.CLASS] == source_object_class:
            x_to_move.append(value[P.OBJECT])

    # Extend the dimensions of the entities and add to a list 
    moved_values = []
    for object1 in x_to_move:
        relationships_add = target_final[object1]
        for object2, object3, object4 in relationships_add:
            moved_values.append((target_relationship_class, (object2, object3, object1, object4)))

    data.setdefault("relationships", []).extend(moved_values)
    import_data(out_db, **data)


    # Parameter values
    data = export_data(in_db)

    # Add the parameter values from the source class to a list
    x_to_move = []
    for value in data["object_parameter_values"]:
        if value[P.CLASS] == source_object_class and value[P.NAME] in parameters:           
            x_to_move.append((value[P.OBJECT], parameters[value[P.NAME]], value[P.X], value[P.ALTERNATIVE]))

    # Add the previous parameter values to a list with the extended relationship dimensions 
    moved_values = []
    for object1, new_parameter, x, alternative in x_to_move:
        relationships_add = target_final[object1]
        for object2, object3, object4 in relationships_add:
            moved_values.append((target_relationship_class, (object2, object3, object1, object4), new_parameter, x, alternative))

    data.setdefault("relationship_parameter_values", []).extend(moved_values)
    import_data(out_db, **data)

def add_parameter_dimension_copy(parameters, source_relationship_class, link_relationship_class, target_relationship_class):
    subquery = in_db.wide_relationship_class_sq
    class_row = in_db.query(subquery).filter(subquery.c.name == link_relationship_class).first()
    subquery = in_db.wide_relationship_sq

    # Create a dictionary that links the new dimension to one of the old dimensions
    target_objects = {}
    for relationship_row in in_db.query(subquery).filter(subquery.c.class_id == class_row.id):
        target, source = relationship_row.object_name_list.split(",")
        target_objects[source] = target

    # Entities
    data = export_data(in_db)

    # Add the entities from the source class to a list
    x_to_move = []
    for value in data["relationships"]:
        if value[P.CLASS] == source_relationship_class:
            x_to_move.append(value[P.OBJECT])

    # Extend the dimensions of the entities and add to a list 
    moved_values = []
    for object1, object2 in x_to_move:
        object_add = target_objects[object1]
        moved_values.append((target_relationship_class, (object_add, object1, object2)))
        moved_values.append((target_relationship_class, (object_add, object2, object1)))
        
    data.setdefault("relationships", []).extend(moved_values)
    import_data(out_db, **data)

    # Parameter values
    data = export_data(in_db)

    # Add the parameter values from the source class to a list
    x_to_move = []
    for value in data["relationship_parameter_values"]:
        if value[P.CLASS] == source_relationship_class and value[P.NAME] in parameters:           
            x_to_move.append((value[P.OBJECT], parameters[value[P.NAME]], value[P.X], value[P.ALTERNATIVE]))

    # Add the previous parameter values to a list with the extended relationship dimensions
    moved_values = []
    for (object1, object2), new_parameter, x, alternative in x_to_move:
        object_add = target_objects[object1]
        moved_values.append((target_relationship_class, (object_add, object1, object2), new_parameter, x, alternative))
        moved_values.append((target_relationship_class, (object_add, object2, object1), new_parameter, x, alternative))

    data.setdefault("relationship_parameter_values", []).extend(moved_values)
    import_data(out_db, **data)

def add_parameter_dimension_change_order(parameters, source_relationship_class, link_relationship_class, target_relationship_class):
    subquery = in_db.wide_relationship_class_sq
    class_row = in_db.query(subquery).filter(subquery.c.name == link_relationship_class).first()
    subquery = in_db.wide_relationship_sq

    # Create a dictionary that links the new dimension to one of the old dimensions
    target_objects = {}
    for relationship_row in in_db.query(subquery).filter(subquery.c.class_id == class_row.id):
        target, source = relationship_row.object_name_list.split(",")
        target_objects[source] = target

    # Entities
    data = export_data(in_db)

    # Add the entities from the source class to a list
    x_to_move = []
    for value in data["relationships"]:
        if value[P.CLASS] == source_relationship_class:
            x_to_move.append(value[P.OBJECT])

    # Extend the dimensions of the entities and add to a list 
    moved_values = []
    for object1, object2, object3 in x_to_move:
        object_add = target_objects[object1]
        if object3 == "rightward":
            moved_values.append((target_relationship_class, (object_add, object1, object2)))
        if object3 == "leftward":
            moved_values.append((target_relationship_class, (object_add, object2, object1)))
        
    data.setdefault("relationships", []).extend(moved_values)
    import_data(out_db, **data)

    # Parameter values
    data = export_data(in_db)

    # Add the parameter values from the source class to a list
    x_to_move = []
    for value in data["relationship_parameter_values"]:
        if value[P.CLASS] == source_relationship_class and value[P.NAME] in parameters:           
            x_to_move.append((value[P.OBJECT], parameters[value[P.NAME]], value[P.X], value[P.ALTERNATIVE]))

    # Add the previous parameter values to a list with the extended relationship dimensions
    moved_values = []
    for (object1, object2, object3), new_parameter, x, alternative in x_to_move:
        object_add = target_objects[object1]
        if object3 == "rightward":
            moved_values.append((target_relationship_class, (object_add, object1, object2), new_parameter, x, alternative))
        if object3 == "leftward":
            moved_values.append((target_relationship_class, (object_add, object2, object1), new_parameter, x, alternative))

    data.setdefault("relationship_parameter_values", []).extend(moved_values)
    import_data(out_db, **data)
    
def add_parameter_dimension_change_order_v2(parameters, source_relationship_class, link_relationship_class, target_relationship_class):
    subquery = in_db.wide_relationship_class_sq
    class_row = in_db.query(subquery).filter(subquery.c.name == link_relationship_class).first()
    subquery = in_db.wide_relationship_sq

    # Create a dictionary that links the new dimension to one of the old dimensions
    target_objects = {}
    for relationship_row in in_db.query(subquery).filter(subquery.c.class_id == class_row.id):
        target, source = relationship_row.object_name_list.split(",")
        target_objects[source] = target

    # Entities
    data = export_data(in_db)

    # Add the entities from the source class to a list
    x_to_move = []
    for value in data["relationships"]:
        if value[P.CLASS] == source_relationship_class:
            x_to_move.append(value[P.OBJECT])

    # Extend the dimensions of the entities and add to a list 
    moved_values = []
    for object1, object2, object3, object4, object5 in x_to_move:
        object_add = target_objects[object1]
        if object3 == "rightward":
            moved_values.append((target_relationship_class, (object_add, object1, object2, object4)))
        if object3 == "leftward":
            moved_values.append((target_relationship_class, (object_add, object2, object1, object4)))
        
    data.setdefault("relationships", []).extend(moved_values)
    import_data(out_db, **data)

    # Parameter values
    data = export_data(in_db)

    # Add the parameter values from the source class to a list
    x_to_move = []
    for value in data["relationship_parameter_values"]:
        if value[P.CLASS] == source_relationship_class and value[P.NAME] in parameters:           
            x_to_move.append((value[P.OBJECT], parameters[value[P.NAME]], value[P.X], value[P.ALTERNATIVE]))

    # Add the previous parameter values to a list with the extended relationship dimensions
    moved_values = []
    for (object1, object2, object3, object4, object5), new_parameter, x, alternative in x_to_move:
        object_add = target_objects[object1]
        if object3 == "rightward":
            moved_values.append((target_relationship_class, (object_add, object1, object2, object4), object5, x, alternative))
        if object3 == "leftward":
            moved_values.append((target_relationship_class, (object_add, object2, object1, object4), object5, x, alternative))

    data.setdefault("relationship_parameter_values", []).extend(moved_values)
    import_data(out_db, **data)

def remove_parameter_dimension(parameters, source_relationship_class, target_relationship_class, minmax):
    # Entities
    data = export_data(in_db)

    # Add the entities from the source class to a list
    x_to_move = []
    for value in data["relationships"]:
        if value[P.CLASS] == source_relationship_class:
            x_to_move.append(value[P.OBJECT])

    # Reduce the dimensions of the entities and add to a list  
    moved_values = []
    for object1, object2, object3 in x_to_move:
        moved_values.append((target_relationship_class, (object1, object2)))
        
    data.setdefault("relationships", []).extend(moved_values)
    import_data(out_db, **data)

    # Parameter values
    data = export_data(in_db)

    # Add the parameter values from the source class to a dict
    x_to_move = {}
    for value in data["relationship_parameter_values"]:
        if value[P.CLASS] == source_relationship_class and value[P.NAME] in parameters:
            object1, object2, object3 = value[P.OBJECT]
            if (object1, object2, parameters[value[P.NAME]], value[P.ALTERNATIVE]) not in x_to_move:
                x_to_move[(object1, object2, parameters[value[P.NAME]], value[P.ALTERNATIVE])] = list()
            x_to_move[(object1, object2, parameters[value[P.NAME]], value[P.ALTERNATIVE])].extend([value[P.X]])

    # Add the previous parameter values to a list with the reduced relationship dimensions
    moved_values = []
    for object1, object2, new_parameter, alternative in x_to_move:
        if minmax == "min":
            x = min(x_to_move[(object1, object2, new_parameter, alternative)])
        if minmax == "max":
            x = max(x_to_move[(object1, object2, new_parameter, alternative)])
        moved_values.append((target_relationship_class, (object1, object2), new_parameter, x, alternative))
            
    data.setdefault("relationship_parameter_values", []).extend(moved_values)
    import_data(out_db, **data)
    

def add_and_remove_parameter_dimension(parameters, source_relationship_class, link_relationship_class, target_relationship_class, minmax):
    subquery = in_db.wide_relationship_class_sq
    class_row = in_db.query(subquery).filter(subquery.c.name == link_relationship_class).first()
    subquery = in_db.wide_relationship_sq

    # Create a dictionary that links the new dimension to one of the old dimensions
    target_objects = {}
    for relationship_row in in_db.query(subquery).filter(subquery.c.class_id == class_row.id):
        target, source = relationship_row.object_name_list.split(",")
        target_objects[source] = target

    # Entities
    data = export_data(in_db)

    # Add the entities from the source class to a list
    x_to_move = []
    for value in data["relationships"]:
        if value[P.CLASS] == source_relationship_class:
            x_to_move.append(value[P.OBJECT])

    # Update the dimensions of the entities and add to a list 
    moved_values = []
    for object1, object2, object3, object4 in x_to_move:
        object_add = target_objects[object1]
        moved_values.append((target_relationship_class, (object_add, object1, object2, object3)))
        
    data.setdefault("relationships", []).extend(moved_values)
    import_data(out_db, **data)

    # Parameter values
    data = export_data(in_db)

    # Add the parameter values from the source class to a dict
    x_to_move = {}
    for value in data["relationship_parameter_values"]:
        if value[P.CLASS] == source_relationship_class and value[P.NAME] in parameters:
            object1, object2, object3, object4 = value[P.OBJECT]
            if (object1, object2, object3, parameters[value[P.NAME]], value[P.ALTERNATIVE]) not in x_to_move:
                x_to_move[(object1, object2, object3, parameters[value[P.NAME]], value[P.ALTERNATIVE])] = list()
            x_to_move[(object1, object2, object3, parameters[value[P.NAME]], value[P.ALTERNATIVE])].extend([value[P.X]])

    # Add the previous parameter values to a list with the updated relationship dimensions
    moved_values = []
    for object1, object2, object3, new_parameter, alternative in x_to_move:
        object_add = target_objects[object1]
        if minmax == "min":
            x = min(x_to_move[(object1, object2, object3, new_parameter, alternative)])
        if minmax == "max":
            x = max(x_to_move[(object1, object2, object3, new_parameter, alternative)])
        moved_values.append((target_relationship_class, (object_add, object1, object2, object3), new_parameter, x, alternative))
            
    data.setdefault("relationship_parameter_values", []).extend(moved_values)
    import_data(out_db, **data)
    
def add_and_remove_parameter_dimension_v2(parameters, source_relationship_class, link_relationship_class, target_relationship_class):
    subquery = in_db.wide_relationship_class_sq
    class_row = in_db.query(subquery).filter(subquery.c.name == link_relationship_class).first()
    subquery = in_db.wide_relationship_sq

    # Create a dictionary that links the new dimension to one of the old dimensions
    target_objects = {}
    for relationship_row in in_db.query(subquery).filter(subquery.c.class_id == class_row.id):
        target, source = relationship_row.object_name_list.split(",")
        target_objects[source] = target

    # Entities
    data = export_data(in_db)

    # Add the entities from the source class to a list
    x_to_move = []
    for value in data["relationships"]:
        if value[P.CLASS] == source_relationship_class:
            x_to_move.append(value[P.OBJECT])

    # Update the dimensions of the entities and add to a list 
    moved_values = []
    for object1, object2, object3, object4 in x_to_move:
        object_add = target_objects[object1]
        moved_values.append((target_relationship_class, (object_add, object1, object2, object3)))
        
    data.setdefault("relationships", []).extend(moved_values)
    import_data(out_db, **data)

    # Parameter values
    data = export_data(in_db)

    # Add the parameter values from the source class to a list
    x_to_move = []
    for value in data["relationship_parameter_values"]:
        if value[P.CLASS] == source_relationship_class and value[P.NAME] in parameters:
            x_to_move.append((value[P.OBJECT], value[P.X], value[P.ALTERNATIVE]))

    # Add the previous parameter values to a list with the updated relationship dimensions
    moved_values = []
    for (object1, object2, object3, new_parameter), x, alternative in x_to_move:
        object_add = target_objects[object1]
        moved_values.append((target_relationship_class, (object_add, object1, object2, object3), new_parameter, x, alternative))
            
    data.setdefault("relationship_parameter_values", []).extend(moved_values)
    import_data(out_db, **data)
    
def main():
    try:       
        #grid__node__unit__io relationships and parameters
        add_parameter_dimension(parameters_gnu, source_relationship_class_gnu, link_relationship_class_gnu, target_relationship_class_gnu)
        add_parameter_dimension(parameters_gnu2, source_relationship_class_gnu, link_relationship_class_gnu, target_relationship_class_gnu)
        add_parameter_dimension_2links_v2(parameters_u, source_object_class_u, link_relationship_class_u, link_relationship_class2_u, target_relationship_class_u)
        
        #grid__node__unit__restype relationships and parameters
        add_and_remove_parameter_dimension(parameters_gnur_min, source_relationship_class_gnur, link_relationship_class_cn, target_relationship_class_gnur, "min")
        add_and_remove_parameter_dimension(parameters_gnur_max, source_relationship_class_gnur, link_relationship_class_cn, target_relationship_class_gnur, "max")
        add_and_remove_parameter_dimension_v2(parameters_gnur, source_relationship_class_gnur, link_relationship_class_cn, target_relationship_class_gnur)
        
        #flow__node relationships and parameters
        add_parameter_dimension_2links(parameters_fn, source_object_class_fn, link_relationship_class_fn, link_relationship_class2_fn, target_relationship_class_fn)
        
        #grid__node__node relationships and parameters
        add_parameter_dimension_copy(parameters_gnn, source_relationship_class_gnn, link_relationship_class_gnn, target_relationship_class_gnn)
        add_parameter_dimension_change_order(parameters_gnn_dir, source_relationship_class_gnn_dir, link_relationship_class_gnn, target_relationship_class_gnn)
        
        #grid__node__node__restype relationships and parameters
        add_parameter_dimension_change_order_v2(parameters_gnnr, source_relationship_class_gnnr, link_relationship_class_gnn, target_relationship_class_gnnr)
        
        #group__restype relationships and parameters
        remove_parameter_dimension(parameters_gr_min, source_relationship_class_gr, target_relationship_class_gr, "min")
        remove_parameter_dimension(parameters_gr_max, source_relationship_class_gr, target_relationship_class_gr, "max")
       
        out_db.commit_session(f"Importing data from the common database.")
    finally:
        in_db.connection.close()
        out_db.connection.close()

main()