def run(payload: dict) -> dict:
    orders = payload.get("orders") or []
    question = payload.get("question") or ""
    limit = payload.get("limit")
    if not isinstance(orders, list):
        raise ValueError("payload.orders must be a list")
    if not isinstance(question, str):
        raise ValueError("payload.question must be text")
    if not isinstance(limit, int):
        try:
            limit = int(limit)
        except Exception:
            limit = 25
    if limit <= 0:
        limit = 25
    limit = min(limit, 50)

    indexed = list(enumerate(orders))
    indexed.sort(key=lambda pair: _order_sort_key(pair[0], pair[1]))
    ordered = [order for _, order in indexed]

    if not ordered:
        context = "Orders: (none found)"
    else:
        total_count = len(ordered)
        show_count = min(limit, total_count)
        header = f"Orders (N={total_count}, showing up to {show_count}):"
        lines = []
        for order in ordered[:show_count]:
            line = (
                f"- id={_field(order.get('order_id') or order.get('id'))} "
                f"region={_field(order.get('region'))} "
                f"returned={_bool_field(order.get('returned'))} "
                f"reason={_field(order.get('return_reason'))} "
                f"total={_field(order.get('total_usd'))}"
            )
            lines.append(line)
        context = header + "\n" + "\n".join(lines)

    prompt = (
        f"{context}\n\n"
        f"Question: {question}\n"
        "Answer using ONLY the order data above. If data is missing, say what is missing."
    )
    return {"prompt": prompt}


def _order_sort_key(index: int, order: object) -> tuple[int, str, int]:
    if not isinstance(order, dict):
        return (1, "", index)
    order_id = order.get("order_id") or order.get("id")
    if order_id is None:
        return (1, "", index)
    return (0, str(order_id), index)


def _field(value: object) -> str:
    if value is None:
        return "-"
    text = str(value).strip()
    return text if text else "-"


def _bool_field(value: object) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "-"
