import json
import time
import subprocess
import requests

API_URL = "http://127.0.0.1:9999/api/admin/governance"

def run_e2e_test():
    print("--- 启动 E2E 治理全链路功能测试 ---")
    
    # 1. Start Server
    server_process = subprocess.Popen(
        ["uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "9999"],
        cwd="/Users/lucas/repos/review/008-review-control-plane/apps/api",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(3) # Wait for server to start
    
    try:
        # 2. Get Bases
        print("\n[+] 验证 GET /bases")
        res = requests.get(f"{API_URL}/bases")
        res.raise_for_status()
        bases = res.json()
        print(f"成功获取 {len(bases)} 个依据档案. (示例: {bases[0]['basis_id']})")
        
        # 3. Create Draft
        print("\n[+] 验证 POST /drafts (创建 Draft)")
        draft_payload = {
            "entity_type": "pack",
            "entity_id": "review.visibility",
            "changes": {
                "display_name": "可见性拦截规则包 (E2E测试修改版)",
                "priority": "critical_tested"
            }
        }
        res = requests.post(f"{API_URL}/drafts", json=draft_payload)
        res.raise_for_status()
        draft = res.json()
        draft_id = draft["id"]
        print(f"成功创建 Draft, ID: {draft_id}, 状态: {draft['status']}")
        
        # 4. List Drafts
        print("\n[+] 验证 GET /drafts")
        res = requests.get(f"{API_URL}/drafts")
        res.raise_for_status()
        drafts = res.json()
        print(f"成功获取草稿列表, 共 {len(drafts)} 条.")
        
        # 5. Publish Draft
        print("\n[+] 验证 POST /drafts/{id}/publish (审批并运用修改)")
        res = requests.post(f"{API_URL}/drafts/{draft_id}/publish")
        res.raise_for_status()
        published_draft = res.json()
        print(f"成功发布 Draft, 最新状态: {published_draft['status']}")
        
        # 6. Verify config YAML has been updated safely
        print("\n[+] 验证 YAML 原文件覆盖保护 (ruamel.yaml)")
        with open("/Users/lucas/repos/review/008-review-control-plane/config/review_basis/pack_registry.yaml", "r", encoding="utf-8") as f:
            content = f.read()
            if "可见性拦截规则包 (E2E测试修改版)" in content and "critical_tested" in content:
                print("成功！YAML 文件数据已变更且缩进保留。")
            else:
                print("失败！YAML 文件没有包含预期修改！")
                
            if "# Governs the valid packs within the system." in content:
                print("成功！YAML 顶部注释(Comments)被顺利保留！")
            else:
                print("警报！YAML 顶部注释丢失，说明 ruamel 失败降级了！")
                
    finally:
        server_process.terminate()
        server_process.wait()
        
        print("\n[+] 撤销测试产生的文件变更")
        subprocess.run(["git", "restore", "/Users/lucas/repos/review/008-review-control-plane/config/review_basis/pack_registry.yaml"])
        print("--- 测试结束 ---")

if __name__ == "__main__":
    run_e2e_test()
