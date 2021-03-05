import sys
import csv
import spinedb_api

from spine_db_transformation import SpineDBTransformation

input_db_url = sys.argv[1]
output_db_url = sys.argv[2]
translation_file = sys.argv[3]

input_db = SpineDBTransformation(input_db_url)
output_db = SpineDBTransformation(output_db_url, create=True)

# Export data from input db
input_data = input_db.export_data()

pass_throughs = dict()
renames = dict()
new_entities = dict()
pass_parameters = dict()

# Open and read transforms file
with open(translation_file) as csvfile:
    for row in csv.reader(csvfile):
        transform_type = row[0].strip()
        if transform_type == "pass_through_entity":
            pass_throughs[row[1].strip()] = row[2:]
        elif transform_type == "rename":
            renames[row[1].strip()] = row [2:]
        elif transform_type == "new_entity":
            new_entities[row[1].strip()] = row[2:]
        elif transform_type == "pass_parameter":
            pass_parameters[row[1].strip()] = row[2:]


# def transform_pass_throughs(input_data: dict, pass_throughs: dict) -> dict:


def transform_rename(transformed, transforms: dict, self=None) -> dict:
    """Translate Spine data renaming classes and parameters
    """

    # Create new data by transforms
    for renam in transforms.items():
        for i, obj_class in enumerate(transformed['object_classes']):
            if obj_class[0] == renam[0]:
                transformed['object_classes'][i] = (renam[1][0],) + transformed['object_classes'][i][1:]
        for i, rel_class in enumerate(transformed['relationship_classes']):
            if rel_class[0] == renam[0]:
                transformed['relationship_classes'][i] = (renam[1][0],) + transformed['relationship_classes'][i][1:]
            for j, obj_class_in_rel_class in enumerate(rel_class[1]):
                if obj_class_in_rel_class == renam[0]:
                    transformed['relationship_classes'][i] = transformed['relationship_classes'][i][0] + (renam[1][j],) + transformed['relationship_classes'][i][1:]

    return transformed

"""
        input_data = {
        'object_classes': [
            (rename(obj_class[0]),) + obj_class[1:]
            for obj_class in input_data['object_classes']
        ],
        'relationship_classes': [
            (
                rename(rel_class[0]),
                [rename(obj_class) for obj_class in rel_class[1]],
                rel_class[2]
            )
            for rel_class in input_data['relationship_classes']
        ],
        'object_parameters': [
            (rename(obj_par[0]), rename(obj_par[1])) + obj_par[2:]
            for obj_par in input_data['object_parameters']
        ],
        'objects': [
            (rename(obj[0]),) + obj[1:]
            for obj in input_data['objects']
        ],
        'relationships': [
            (rename(rel[0]), rel[1]) for rel in input_data['relationships']
        ],
        'object_parameter_values': [
            (
                rename(par_value[0]),
                par_value[1],
                rename(par_value[2])
            ) + par_value[3:]
            for par_value in input_data['object_parameter_values']
        ],
        #        'features': [
        #            (
        #                rename(feature[0]),
        #                rename(feature[1]),
        #                rename(feature[2]),
        #                feature[3]
        #            )
        #            for feature in input_data['features']
        #        ],
        #        'tool_features': [
        #            (
        #                tool_feature[0],
        #                rename(tool_feature[1]),
        #                rename(tool_feature[2]),
        #                tool_feature[3],
        #            )
        #            for tool_feature in input_data['tool_features']
        #        ],
    }

    # Pass through keys which are not renamed
    #for key in (set(input_data.keys()) - set(translated.keys())):
    #    translated.update({key: input_data[key]})

    return input_data
"""

output_data = transform_rename(input_data, renames)

# Store to output db
output_db.import_data(output_data)
output_db.commit("Translate from Master data")
