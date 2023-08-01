'''
bloodhound 查询的数据解析
比如以下查询会输出大量数据，影响bloodhound 渲染，导出json，然后输出为text 会更好
MATCH p=(u:User)-[r1:GenericAll]->(c:Computer) WHERE u.domain = $result RETURN p
'''
import json
import csv


with open('data.json','r',encoding="utf-8") as f:
    data = json.load(f)

# Create a mapping from id to label
id_to_label = {node['id']: node['label'] for node in data['nodes']}

# Create a dictionary to store targets for each source
source_to_targets = {}

# Populate the source_to_targets dictionary
for edge in data['edges']:
    source_id = edge['source']
    target_id = edge['target']
    source_label = id_to_label[source_id]
    target_label = id_to_label[target_id]

    # Check if the source ID already exists in the dictionary
    if source_id in source_to_targets:
        source_to_targets[source_id].append(target_label)
    else:
        source_to_targets[source_id] = [target_label]



with open('output.txt', 'w', encoding='utf-8') as txtfile:

    # Write each block of data
    for source_id, target_labels in source_to_targets.items():
        source_label = id_to_label[source_id]
        txtfile.write(f'Object: {source_label} => Members:\n')
        txtfile.write('-' * 60 + '\n')

        for target_label in target_labels:  # Loop through each target
            txtfile.write('\t' + target_label + '\n')

        txtfile.write('\n')  # Add a blank line after each group


