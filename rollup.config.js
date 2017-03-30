import npm from "rollup-plugin-node-resolve";

export default {
  entry: "rollup-entry.js",
  format: "umd",
  moduleName: "d3",
  plugins: [npm({jsnext: true})],
  dest: "static/javascripts/d3-ccaa.js"
};
