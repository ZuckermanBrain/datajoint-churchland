# Listing available schema
dj.list_schemas()

# Dropping a schema
schema = dj.schema('schema_name')
schema.drop()

# Printing an ERD to file
dj.ERD(schema).save(filename='file_name.png')

# Get a list of uncomputed keys
(query.key_source - query).proj()