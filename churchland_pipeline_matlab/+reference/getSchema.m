function obj = getSchema
persistent schemaObject
if isempty(schemaObject)
    schemaObject = dj.Schema(dj.conn, 'reference', 'churchland_common_reference');
end
obj = schemaObject;
end
