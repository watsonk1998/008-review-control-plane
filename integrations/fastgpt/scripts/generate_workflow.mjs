import path from 'node:path';
import { generateBundle } from './workflow_bundle_lib.mjs';

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), '../../..');
const result = generateBundle({ repoRoot });
console.log(`已生成 FastGPT 主工作流与工作流工具 bundle：${result.artifactsDir}`);
