function obj = getSchema
persistent schemaObject
if isempty(schemaObject)
    schemaObject = dj.Schema(dj.conn, 'acquisition', 'churchland_common_acquisition');
end
obj = schemaObject;
end
