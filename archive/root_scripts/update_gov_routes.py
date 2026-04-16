import re

path = "apps/api/src/routes/admin/governance.py"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

write_routes = """
@router.post("/bases")
async def save_bases(data: dict[str, Any]):
    service = get_governance_service()
    service.save_bases(data)
    return {"status": "success"}

@router.post("/packs")
async def save_packs(data: dict[str, Any]):
    service = get_governance_service()
    service.save_packs(data)
    return {"status": "success"}

@router.post("/rule-packs")
async def save_rule_packs(data: dict[str, Any]):
    service = get_governance_service()
    service.save_rule_packs(data)
    return {"status": "success"}

@router.post("/profiles")
async def save_profiles(data: dict[str, Any]):
    service = get_governance_service()
    service.save_profile_mapping(data)
    return {"status": "success"}
"""

idx = text.find("# --- Candidates ---")
text = text[:idx] + write_routes + "\n" + text[idx:]

with open(path, "w", encoding="utf-8") as f:
    f.write(text)

print("Updated Governance Routes with POST abilities!")
