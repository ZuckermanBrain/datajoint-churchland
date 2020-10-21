function obj = getSchema
persistent schemaObject
if isempty(schemaObject)
    schemaObject = dj.Schema(dj.conn, 'processing', 'churchland_analyses_processing');
end
obj = schemaObject;
end
