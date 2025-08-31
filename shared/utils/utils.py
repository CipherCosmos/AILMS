# Utility functions for the LMS backend
def serialize_mongo_doc(doc):
    """Convert MongoDB document to JSON-serializable format"""
    if not doc:
        return doc

    # Handle ObjectId at top level
    if isinstance(doc, __import__('bson').ObjectId):
        return str(doc)

    if isinstance(doc, list):
        return [serialize_mongo_doc(item) for item in doc]

    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, __import__('bson').ObjectId):
                result[key] = str(value)
            elif isinstance(value, dict):
                result[key] = serialize_mongo_doc(value)
            elif isinstance(value, list):
                result[key] = serialize_mongo_doc(value)
            else:
                result[key] = value
        return result

    return doc