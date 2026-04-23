    import fs from 'node:fs';
    import path from 'node:path';

    const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../..');
    const artifactsDir = path.join(repoRoot, 'artifacts', 'fastgpt');
    const generatedDir = path.join(repoRoot, 'integrations', 'fastgpt', 'toolset', 'hermesStructuredReview', 'assets', 'generated');
    fs.mkdirSync(artifactsDir, { recursive: true });

    const templates = JSON.parse(fs.readFileSync(path.join(generatedDir, 'template_manifest.json'), 'utf8'));
    const moduleBindings = JSON.parse(fs.readFileSync(path.join(generatedDir, 'module_bindings.json'), 'utf8'));
    const docTypes = Object.keys(JSON.parse(fs.readFileSync(path.join(generatedDir, 'profile_mapping.json'), 'utf8')));

    const rows = [
      ['能力', '现状', '说明'],
      ['buildReviewContext', 'implemented', 'TS 工具内置文档读取、解析、facts、profile、basis、rule/candidate 生成'],
      ['runSupportReview008', 'implemented', 'TS 工具输出 supportResult008 / supportPacket008 / supportLayerContext'],
      ['runDeterministicReviewer', 'implemented', '支持 visibility_gap / policy_compliance / normative_validity'],
      ['assembleFinalDecision', 'implemented', '保留 fail-closed、模块门禁、degradedReason 非空'],
      ['renderFormalReport', 'implemented', '输出 Markdown / HTML / CSS / ViewModel，不产出 PDF'],
      ['AI reviewer templates', 'implemented', `已导出 ${templates.length} 个模板`],
      ['Document types', 'implemented', docTypes.join(', ')],
      ['Review modules', 'implemented', Object.keys(moduleBindings).join(', ')],
      ['FastGPT .pkg', 'pending-build', '通过 build_fastgpt_pkg.sh 注入官方 fastgpt-plugin 临时工作区后构建']
    ];

    const md = ['# Hermes -> FastGPT parity / readiness', '', '| 能力 | 现状 | 说明 |', '|---|---|---|'];
    for (const row of rows.slice(1)) md.push(`| ${row[0]} | ${row[1]} | ${row[2]} |`);
    md.push('', '## Import readiness', '', '- Workflow JSON generated into `/artifacts/fastgpt`', '- Governed assets exported from the Python source of truth', '- Toolset source is present under `/integrations/fastgpt/toolset/hermesStructuredReview`', '- Official `.pkg` build requires Bun + temporary clone of `labring/fastgpt-plugin`');

    fs.writeFileSync(path.join(artifactsDir, 'hermes-fastgpt-parity-matrix.md'), md.join('
'));
    fs.writeFileSync(path.join(artifactsDir, 'hermes-fastgpt-import-readiness.md'), md.join('
'));
    console.log('Generated parity/readiness reports in', artifactsDir);
