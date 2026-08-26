# chatbot/app/package_generator.py
from typing import Any

def generate_packages(
    main_courses: list[Any], addons: list[Any], duration: int | None = None
) -> list[dict[str, Any]]:
    """Generates package combinations from main courses and add-ons."""
    all_packages = []

    def _get_field_value(item: Any, field_name: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(field_name, default)
        return getattr(item, field_name, default)

    # 1. Basic packages (main courses only)
    for course in main_courses:
        for d in _get_field_value(course, "durations", []):
            all_packages.append({
                "name": f'{_get_field_value(course, "courseName")} {d.duration} min',
                "totalDuration": d.duration,
                "totalPrice": d.price,
                "course": {
                    "course_id": _get_field_value(course, "courseId"),
                    "name": _get_field_value(course, "courseName"),
                    "duration": d.duration,
                    "price": d.price,
                },
                "addons": [],
            })

    # 2. Combo packages (main course + one add-on)
    for course in main_courses:
        for d in _get_field_value(course, "durations", []):
            for addon in addons:
                for addon_duration in _get_field_value(addon, "durations", []):
                    total_duration = d.duration + addon_duration.duration
                    all_packages.append({
                        "name": f'{_get_field_value(course, "courseName")} {d.duration} min\n+ {_get_field_value(addon, "courseName")} {addon_duration.duration} min',
                        "totalDuration": total_duration,
                        "totalPrice": d.price + addon_duration.price,
                        "course": {
                            "course_id": _get_field_value(course, "courseId"),
                            "name": _get_field_value(course, "courseName"),
                            "duration": d.duration,
                            "price": d.price,
                        },
                        "addons": [{
                            "addon_id": _get_field_value(addon, "courseId"),
                            "name": _get_field_value(addon, "courseName"),
                            "duration": addon_duration.duration,
                            "price": addon_duration.price,
                        }],
                    })

    if duration:
        all_packages = [p for p in all_packages if p["totalDuration"] == duration]

    return sorted(all_packages, key=lambda p: p["totalPrice"])
