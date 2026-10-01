from math import ceil

from flask import jsonify, request


def ok(**payload):
    payload.setdefault("success", True)
    return jsonify(payload)


def error(message, status=400, **extra):
    payload = {"success": False, "error": message}
    payload.update(extra)
    return jsonify(payload), status


def pagination_args(default_per_page=20, max_per_page=100):
    page = max(int(request.args.get("page", 1) or 1), 1)
    per_page = min(max(int(request.args.get("per_page", default_per_page) or default_per_page), 1), max_per_page)
    return page, per_page


def paginate(query, serializer=lambda item: item.to_dict(), default_per_page=20):
    page, per_page = pagination_args(default_per_page=default_per_page)
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return {
        "items": [serializer(item) for item in items],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "pages": ceil(total / per_page) if per_page else 0,
        },
    }
