def paginate(query, page=1, size=20):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    
    return {
        'items': items,
        'pagination': {
            'page': page,
            'size': size,
            'total': total,
            'totalPages': (total + size - 1) // size
        }
    }
