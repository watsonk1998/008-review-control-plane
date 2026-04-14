import os
import requests
import json
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

APP_ID = "cli_a949c09281fa5bca"
APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "changeme")
WIKI_TOKEN = "AebpwOoLRii46okbQkScuOYLnGb"
APP_TOKEN = "MpB2bqEcsaVYZSs0nNKcRm5Anrg"

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    res = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
    return res.json().get("tenant_access_token")

def create_table(app_token, name, tat):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables"
    res = requests.post(url, headers={"Authorization": f"Bearer {tat}", "Content-Type": "application/json"}, json={"table": {"name": name, "default_view_name": "默认视图"}})
    table_id = res.json().get("data", {}).get("table_id")
    if not table_id:
        print("Error creating table:", res.json())
        return None
    return table_id

def add_field(app_token, table_id, field_name, field_type, tat):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    res = requests.post(url, headers={"Authorization": f"Bearer {tat}", "Content-Type": "application/json"}, json={"field_name": field_name, "type": field_type})
    print(f"Add field {field_name}:", res.json())
    return

def batch_create_records(app_token, table_id, records, tat):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
    # Filter out empty string values to avoid type errors
    clean_records = []
    for r in records:
        clean_fields = {k: v for k, v in r.items() if v}
        clean_records.append({"fields": clean_fields})
        
    payload = {"records": clean_records}
    res = requests.post(url, headers={"Authorization": f"Bearer {tat}", "Content-Type": "application/json"}, json=payload)
    print(f"Insert records in {table_id}:", res.json())

def setup_table(tat, app_token, table_name, columns, data):
    table_id = create_table(app_token, table_name, tat)
    if not table_id: return
    print(f"Created table {table_name}: {table_id}")
    time.sleep(1)
    
    # Get fields
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields"
    res = requests.get(url, headers={"Authorization": f"Bearer {tat}"})
    fields = res.json().get("data", {}).get("items", [])
    if fields:
        primary_field_id = fields[0]["field_id"]
        # Rename primary field
        url_update = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields/{primary_field_id}"
        requests.put(url_update, headers={"Authorization": f"Bearer {tat}", "Content-Type": "application/json"}, json={"field_name": columns[0]})
        print(f"Renamed primary field to {columns[0]}")
        time.sleep(0.5)
    
    # Add other fields
    for col in columns[1:]:
        add_field(app_token, table_id, col, 1, tat)
        time.sleep(0.5)
        
    # Insert Data
    batch_create_records(app_token, table_id, data, tat)


if __name__ == "__main__":
    tat = get_tenant_access_token()
    if not tat:
        print("Failed to get tat")
        exit(1)

    t1_cols = [
        "标准类型", 
        "标准名称 (按重要性、优先级排序，重点的标红)", 
        "编号 (按重要性、优先级排序，重点的标红)"
    ]
    t1_data = [
        {
            "标准类型": "强制性国家标准GB", 
            "标准名称 (按重要性、优先级排序，重点的标红)": "建筑与市政地基基础通用规范", 
            "编号 (按重要性、优先级排序，重点的标红)": "GB 55003-2021"
        },
        {
            "标准类型": "强制性国家标准GB", 
            "标准名称 (按重要性、优先级排序，重点的标红)": "....", 
            "编号 (按重要性、优先级排序，重点的标红)": ""
        },
        {
            "标准类型": "铁路行业推荐信标准 TB/T", 
            "标准名称 (按重要性、优先级排序，重点的标红)": "铁路信号集中监测系统", 
            "编号 (按重要性、优先级排序，重点的标红)": "TB/T 3602-2025"
        },
        {
            "标准类型": "铁路行业推荐信标准 TB/T", 
            "标准名称 (按重要性、优先级排序，重点的标红)": "....", 
            "编号 (按重要性、优先级排序，重点的标红)": ""
        }
    ]
    
    t2_cols = [
        "大类",
        "方案类型",
        "依据规范 (按优先顺序，重点的标红)",
        "重点审查的依据条文 (按优先级排序，重点的标红)",
        "项目背景资料"
    ]
    t2_data = [
        {
            "大类": "危大工程专项施工方案",
            "方案类型": "通用条款",
            "依据规范 (按优先顺序，重点的标红)": "1、《危险性较大的分部分项工程专项施工方案编制指南》建办质〔2021〕48号\n2、危险性较大的分部分项工程专项施工方案严重缺陷清单（试行）建办质〔2024〕63号",
            "项目背景资料": "1. 项目当地部门、业主的特殊要求\n2. 项目的工程信息（例如图纸中的设计说明文字内容）\n...."
        },
        {
            "大类": "危大工程专项施工方案",
            "方案类型": "起重吊装及安装拆卸工程",
            "依据规范 (按优先顺序，重点的标红)": "1、《建筑施工起重吊装工程安全技术规范》JGJ 276-2012\n2、《起重机械安全规程》GB/T 3811-2008",
            "重点审查的依据条文 (按优先级排序，重点的标红)": "1、《建筑施工起重吊装工程安全技术规范》JGJ 276-2012，第1.X.X条\n2、《建筑施工起重吊装工程安全技术规范》JGJ 276-2012，第2.X.X条\n3、《起重机械安全规程》GB/T 3811-2008，第X.X.X条"
        },
        {
            "大类": "危大工程专项施工方案",
            "方案类型": "基坑工程....."
        },
        {
            "大类": "分部分项工程方案",
            "方案类型": "混凝土工程施工方案...."
        },
        {
            "大类": "施工组织方案"
        }
    ]
    
    t3_cols = [
        "大类",
        "方案类型",
        "依据规范 (按优先级排序，重点的标红)",
        "重点审查的依据条文 (按优先级排序，重点的标红，尽可能写详细)",
        "项目背景资料"
    ]
    t3_data = [
        {
            "大类": "监理规划",
            "方案类型": "监理规划(示例)",
            "依据规范 (按优先级排序，重点的标红)": "1、《建设工程监理规范》GB/T 50319-2013\n2、《建筑和市政地基基础通用规范》GB55003-2021\n3、《建筑和市政工程抗震通用规范》GB55002-2021\n3、《工程结构通用规范》GB55001-2021\n4、《混凝土结构通用规范》GB55008-2021\n5、《钢结构通用规范》GB55006-2021\n.......",
            "重点审查的依据条文 (按优先级排序，重点的标红，尽可能写详细)": "1、《建设工程监理规范》GB/T 50319-2013，第X.X.1条\n2、《建设工程监理规范》GB/T 50319-2013，第X.X.2条\n3、《XXXXX规范》GBXXXX-2020,第X.X.X条",
            "项目背景资料": "1.本项目的监理合同\n2.本项目的工程信息\n...."
        },
        {
            "大类": "监理细则",
            "方案类型": "给排水及环保工程监理实施细则\n....."
        }
    ]

    setup_table(tat, APP_TOKEN, "企业常用标准", t1_cols, t1_data)
    setup_table(tat, APP_TOKEN, "危大工程专项施工方案", t2_cols, t2_data)
    setup_table(tat, APP_TOKEN, "监理规划及实施细则", t3_cols, t3_data)
    print("Done")
