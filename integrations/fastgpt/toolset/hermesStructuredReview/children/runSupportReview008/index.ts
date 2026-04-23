import config from './config';
import { InputType, OutputType, tool as toolCb } from './src/index.js';
import { exportTool } from '@tool/utils/tool';

export default exportTool({
  toolCb,
  InputType,
  OutputType,
  config
});
