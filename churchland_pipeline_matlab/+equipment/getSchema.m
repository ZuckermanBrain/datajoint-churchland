function obj = getSchema
persistent schemaObject
if isempty(schemaObject)
    schemaObject = dj.Schema(dj.conn, 'equipment', 'churchland_common_equipment');
end
obj = schemaObject;
end
