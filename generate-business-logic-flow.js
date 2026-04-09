const fs = require('fs');

const dsl = {
  "version": 2,
  "nodes": [
    {
      "type": "frame",
      "id": "root",
      "x": 0, "y": 0,
      "width": 1400,
      "height": "fit-content",
      "layout": "vertical",
      "gap": 40,
      "padding": 40,
      "children": [
        {
          "type": "text",
          "id": "title",
          "width": "fill-container",
          "height": "fit-content",
          "text": "008 核心风控业务逻辑与审查依据流转图",
          "fontSize": 32,
          "fontWeight": "bold",
          "textAlign": "center",
          "verticalAlign": "middle"
        },
        {
          "type": "frame",
          "id": "flow-container",
          "width": "fill-container",
          "height": "fit-content",
          "layout": "horizontal",
          "alignItems": "stretch",
          "gap": 40,
          "padding": 0,
          "children": [
            {
              "type": "frame",
              "id": "input-layer",
              "width": 280,
              "height": "fill-container",
              "layout": "vertical",
              "alignItems": "stretch",
              "gap": 20,
              "padding": 20,
              "borderRadius": 8,
              "borderWidth": 2,
              "borderColor": "#3370FF",
              "fillColor": "#F0F4FF",
              "children": [
                { "type": "text", "id": "input-title", "width": "fill-container", "height": "fit-content", "text": "输入层: 审查对象", "fontSize": 18, "fontWeight": "bold", "textAlign": "center", "verticalAlign": "middle", "textColor": "#1F2329" },
                { "type": "rect", "id": "in-1", "width": "fill-container", "height": "fit-content", "text": "施工组织设计\n(Construction Org)", "borderRadius": 8, "borderWidth": 2, "borderColor": "#3370FF", "fillColor": "#FFFFFF", "fontSize": 14, "textAlign": "center", "verticalAlign": "middle" },
                { "type": "rect", "id": "in-2", "width": "fill-container", "height": "fit-content", "text": "危大/专项施工方案\n(Hazardous Special)", "borderRadius": 8, "borderWidth": 2, "borderColor": "#3370FF", "fillColor": "#FFFFFF", "fontSize": 14, "textAlign": "center", "verticalAlign": "middle" },
                { "type": "rect", "id": "in-3", "width": "fill-container", "height": "fit-content", "text": "监理实施细则\n(Supervision Plan)", "borderRadius": 8, "borderWidth": 2, "borderColor": "#3370FF", "fillColor": "#FFFFFF", "fontSize": 14, "textAlign": "center", "verticalAlign": "middle" }
              ]
            },
            {
              "type": "frame",
              "id": "engine-layer",
              "width": 400,
              "height": "fill-container",
              "layout": "vertical",
              "alignItems": "stretch",
              "gap": 20,
              "padding": 20,
              "borderRadius": 8,
              "borderWidth": 2,
              "borderColor": "#F54A45",
              "fillColor": "#FEF1F1",
              "children": [
                { "type": "text", "id": "engine-title", "width": "fill-container", "height": "fit-content", "text": "008 引擎: 审查依据与规则匹配", "fontSize": 18, "fontWeight": "bold", "textAlign": "center", "verticalAlign": "middle", "textColor": "#1F2329" },
                {
                  "type": "frame",
                  "id": "rules-wrapper",
                  "width": "fill-container",
                  "height": "fit-content",
                  "layout": "vertical",
                  "gap": 12,
                  "padding": 16,
                  "borderRadius": 8,
                  "borderWidth": 2,
                  "borderColor": "#F54A45",
                  "fillColor": "#FFFFFF",
                  "children": [
                    { "type": "text", "id": "rules-title", "width": "fill-container", "height": "fit-content", "text": "硬性法律法规与标准 (底线)", "fontSize": 14, "fontWeight": "bold", "textAlign": "center", "verticalAlign": "middle", "textColor": "#1F2329" },
                    { "type": "rect", "id": "rule-1", "width": "fill-container", "height": "fit-content", "text": "国家及行业法律法规 / 现行工程规范", "borderRadius": 8, "borderWidth": 1, "borderColor": "#F54A45", "fillColor": "#FFF0F0", "fontSize": 12, "textAlign": "center", "verticalAlign": "middle" }
                  ]
                },
                {
                  "type": "frame",
                  "id": "context-wrapper",
                  "width": "fill-container",
                  "height": "fit-content",
                  "layout": "vertical",
                  "gap": 12,
                  "padding": 16,
                  "borderRadius": 8,
                  "borderWidth": 2,
                  "borderColor": "#F54A45",
                  "fillColor": "#FFFFFF",
                  "children": [
                    { "type": "text", "id": "context-title", "width": "fill-container", "height": "fit-content", "text": "项目级约束上下文 (定制核对)", "fontSize": 14, "fontWeight": "bold", "textAlign": "center", "verticalAlign": "middle", "textColor": "#1F2329" },
                    {
                      "type": "frame",
                      "id": "context-row",
                      "width": "fill-container",
                      "height": "fit-content",
                      "layout": "horizontal",
                      "gap": 8,
                      "padding": 0,
                      "children": [
                        { "type": "rect", "id": "ctx-1", "width": "fill-container", "height": "fit-content", "text": "设计图纸", "borderRadius": 8, "borderWidth": 1, "borderColor": "#F54A45", "fillColor": "#FFF0F0", "fontSize": 12, "textAlign": "center", "verticalAlign": "middle" },
                        { "type": "rect", "id": "ctx-2", "width": "fill-container", "height": "fit-content", "text": "施工合同 / 招投标文件", "borderRadius": 8, "borderWidth": 1, "borderColor": "#F54A45", "fillColor": "#FFF0F0", "fontSize": 12, "textAlign": "center", "verticalAlign": "middle" }
                      ]
                    },
                    { "type": "rect", "id": "ctx-3", "width": "fill-container", "height": "fit-content", "text": "企业级内部管控标准 / 示范文本", "borderRadius": 8, "borderWidth": 1, "borderColor": "#F54A45", "fillColor": "#FFF0F0", "fontSize": 12, "textAlign": "center", "verticalAlign": "middle" }
                  ]
                },
                {
                  "type": "frame",
                  "id": "flywheel-wrapper",
                  "width": "fill-container",
                  "height": "fit-content",
                  "layout": "vertical",
                  "gap": 12,
                  "padding": 16,
                  "borderRadius": 8,
                  "borderWidth": 2,
                  "borderColor": "#F54A45",
                  "fillColor": "#FFFFFF",
                  "children": [
                    { "type": "text", "id": "flywheel-title", "width": "fill-container", "height": "fit-content", "text": "动态隐患语料库 (未言之物)", "fontSize": 14, "fontWeight": "bold", "textAlign": "center", "verticalAlign": "middle", "textColor": "#1F2329" },
                    { "type": "rect", "id": "rule-2", "width": "fill-container", "height": "fit-content", "text": "历史事故调查报告 / 专家纠偏错题本", "borderRadius": 8, "borderWidth": 1, "borderColor": "#F54A45", "fillColor": "#FFF0F0", "fontSize": 12, "textAlign": "center", "verticalAlign": "middle" }
                  ]
                }
              ]
            },
            {
              "type": "frame",
              "id": "expert-layer",
              "width": 280,
              "height": "fill-container",
              "layout": "vertical",
              "alignItems": "stretch",
              "gap": 20,
              "padding": 20,
              "borderRadius": 8,
              "borderWidth": 2,
              "borderColor": "#00B365",
              "fillColor": "#E8F8F2",
              "children": [
                { "type": "text", "id": "expert-title", "width": "fill-container", "height": "fit-content", "text": "人机协同: 确权裁决", "fontSize": 18, "fontWeight": "bold", "textAlign": "center", "verticalAlign": "middle", "textColor": "#1F2329" },
                { "type": "rect", "id": "ex-1", "width": "fill-container", "height": "fit-content", "text": "大声暴露盲区请求介入\n(诚实性底线)", "borderRadius": 8, "borderWidth": 2, "borderColor": "#00B365", "fillColor": "#FFFFFF", "fontSize": 14, "textAlign": "center", "verticalAlign": "middle" },
                { "type": "rect", "id": "ex-2", "width": "fill-container", "height": "fit-content", "text": "基于证据链的专家签批\n(卡片对照UI)", "borderRadius": 8, "borderWidth": 2, "borderColor": "#00B365", "fillColor": "#FFFFFF", "fontSize": 14, "textAlign": "center", "verticalAlign": "middle" },
                { "type": "rect", "id": "ex-3", "width": "fill-container", "height": "fit-content", "text": "专家软阻断与留痕免责\n(职场权力重塑)", "borderRadius": 8, "borderWidth": 2, "borderColor": "#00B365", "fillColor": "#FFFFFF", "fontSize": 14, "textAlign": "center", "verticalAlign": "middle" }
              ]
            },
            {
              "type": "frame",
              "id": "output-layer",
              "width": 240,
              "height": "fill-container",
              "layout": "vertical",
              "alignItems": "stretch",
              "justifyContent": "center",
              "gap": 20,
              "padding": 20,
              "borderRadius": 8,
              "borderWidth": 2,
              "borderColor": "#8F959E",
              "fillColor": "#F8F9FA",
              "children": [
                { "type": "text", "id": "output-title", "width": "fill-container", "height": "fit-content", "text": "输出层: 业务闭环", "fontSize": 18, "fontWeight": "bold", "textAlign": "center", "verticalAlign": "middle", "textColor": "#1F2329" },
                { "type": "rect", "id": "out-1", "width": "fill-container", "height": "fit-content", "text": "限期整改派发单\n(流转至 OA 工单系统)", "borderRadius": 8, "borderWidth": 2, "borderColor": "#8F959E", "fillColor": "#FFFFFF", "fontSize": 14, "textAlign": "center", "verticalAlign": "middle" },
                { "type": "rect", "id": "out-2", "width": "fill-container", "height": "fit-content", "text": "脱敏纠偏反馈数据\n(回流至动态规则库)", "borderRadius": 8, "borderWidth": 2, "borderColor": "#8F959E", "fillColor": "#FFFFFF", "fontSize": 14, "textAlign": "center", "verticalAlign": "middle" }
              ]
            }
          ]
        }
      ]
    },
    { "type": "connector", "connector": { "from": "input-layer", "to": "engine-layer", "fromAnchor": "right", "toAnchor": "left", "lineShape": "straight", "lineWidth": 2, "endArrow": "arrow" } },
    { "type": "connector", "connector": { "from": "engine-layer", "to": "expert-layer", "fromAnchor": "right", "toAnchor": "left", "lineShape": "straight", "lineWidth": 2, "endArrow": "arrow" } },
    { "type": "connector", "connector": { "from": "expert-layer", "to": "output-layer", "fromAnchor": "right", "toAnchor": "left", "lineShape": "straight", "lineWidth": 2, "endArrow": "arrow" } },
    { "type": "connector", "connector": { "from": "out-2", "to": "flywheel-wrapper", "fromAnchor": "bottom", "toAnchor": "bottom", "lineShape": "rightAngle", "lineWidth": 2, "endArrow": "arrow", "strokeColor": "#F54A45" } }
  ]
};

fs.writeFileSync('business-logic-flow.json', JSON.stringify(dsl, null, 2));
console.log('JSON file generated.');
