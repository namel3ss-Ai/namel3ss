def run(payload):
    return {'message': f"Hello {payload.get('name', '')}"}
