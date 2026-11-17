#!/usr/bin/env node
/*
 * Gate 27B — independently recompile Sourcify's ORIGINAL Standard JSON input
 * with the matching pinned Solidity JS compiler. Compare runtime, including
 * metadata, not merely executable prefix. For pool implementations, account
 * for immutable values assigned at construction. Writes only auditable
 * code hashes/lengths and an optional matched runtime hex (no keys).
 */
const fs = require("fs");
const path = require("path");
const crypto = require("crypto");

function checkedHex(x) {
  if (typeof x !== "string" || !/^(0x)?[0-9a-fA-F]*$/.test(x)) {
    throw Error("INVALID_HEX_RUNTIME");
  }
  const y = x.startsWith("0x") ? x.slice(2) : x;
  if (y.length % 2 !== 0) throw Error("ODD_HEX");
  return Buffer.from(y,"hex");
}
function digest(buf) { return crypto.createHash("sha256").update(buf).digest("hex"); }
function applyImmutables(recompiled, immutRefs, values) {
  const patched = Buffer.from(recompiled);
  for (const [id, locs] of Object.entries(immutRefs || {})) {
    const valueStr = values?.immutables?.[id];
    if (!valueStr) throw Error("MISSING_DEPLOYED_IMMUTABLE_"+id);
    const value = checkedHex(valueStr);
    for (const loc of locs) {
      if (!Number.isInteger(loc.start) || !Number.isInteger(loc.length)
          || loc.length !== value.length || loc.start + loc.length > patched.length) {
        throw Error("INVALID_IMMUTABLE_OFFSET_"+id);
      }
      value.copy(patched, loc.start);
    }
  }
  return patched;
}
function run(inputPath, compilerDir, outputPath) {
  const report={input_file:path.basename(inputPath),status:"NOT_RECOMPILED"};
  try {
    const verified=JSON.parse(fs.readFileSync(inputPath,"utf8"));
    const version=verified?.compilation?.compilerVersion;
    const fqn=verified?.compilation?.fullyQualifiedName;
    if (!version || !fqn || !fqn.includes(":")) throw Error("MISSING_SOURCIFY_COMPILER_IDENTITY");
    const compiler=require(path.resolve(compilerDir,"node_modules","solc"));
    const actualVersion=compiler.version();
    if (actualVersion.split("+")[0] !== version.split("+")[0]) throw Error("WRONG_COMPILER_VERSION");
    const input=JSON.parse(JSON.stringify(verified.stdJsonInput));
    if (!input || !input.sources || !input.settings) throw Error("NO_VERIFIED_STANDARD_JSON_INPUT");
    // Compilation outputs do not affect runtime metadata, but solc needs
    // outputSelection explicitly to emit EVM bytecode.
    input.settings.outputSelection={"*":{"*":["evm.deployedBytecode.object",
                                            "evm.deployedBytecode.immutableReferences",
                                            "metadata"]}};
    const out=JSON.parse(compiler.compile(JSON.stringify(input)));
    const errors=(out.errors || []).filter(e => e.severity==="error");
    if (errors.length) throw Error("SOLC_ERRORS_"+errors.slice(0,2).map(e=>e.errorCode||e.type).join("_"));
    const pos=fqn.lastIndexOf(":");
    const source=fqn.slice(0,pos), contract=fqn.slice(pos+1);
    const artifact=out.contracts?.[source]?.[contract];
    if (!artifact?.evm?.deployedBytecode?.object) throw Error("MISSING_RECOMPILED_BYTECODE");
    const fresh=checkedHex(artifact.evm.deployedBytecode.object);
    const published=checkedHex(verified.runtimeBytecode.recompiledBytecode);
    const onchain=checkedHex(verified.runtimeBytecode.onchainBytecode);
    const refs=artifact.evm.deployedBytecode.immutableReferences || {};
    const patched=applyImmutables(fresh,refs,verified.runtimeBytecode.transformationValues);
    const reportedRefs=verified.runtimeBytecode.immutableReferences || {};
    const sameRefs=JSON.stringify(refs)===JSON.stringify(reportedRefs);
    report.compiler_actual=actualVersion;
    report.compiler_expected=version;
    report.fully_qualified_name=fqn;
    report.compiler_settings=input.settings;
    delete report.compiler_settings.outputSelection;
    report.fresh_sha256=digest(fresh);
    report.recompiled_from_sourcify_sha256=digest(published);
    report.expected_onchain_sha256=digest(onchain);
    report.patched_sha256=digest(patched);
    report.byte_lengths={fresh:fresh.length,expected:onchain.length,patched:patched.length};
    report.immutable_offsets_identical=sameRefs;\n    report.immutable_offset_shape_difference_is_nonblocking_if_final_runtime_matches=true;
    report.compiled_runtime_equals_sourcify_recompiled_runtime=fresh.equals(published);
    report.compiled_with_patched_immutables_equals_onchain_runtime=patched.equals(onchain);
    report.full_metadata_matches_as_part_of_runtime=patched.equals(onchain);
    report.sourcify_reported_match=verified.match;
    report.status=(fresh.equals(published)&&patched.equals(onchain))
      ? "INDEPENDENT_FULL_RUNTIME_REPRODUCTION_PASS"
      : "INDEPENDENT_FULL_RUNTIME_REPRODUCTION_MISMATCH";
    fs.writeFileSync(outputPath,JSON.stringify(report,null,2)+"\n");
    process.stdout.write(JSON.stringify({name:path.basename(inputPath),
      status:report.status,sha256:report.patched_sha256,bytes:report.byte_lengths.patched})+"\n");
    return report.status.endsWith("_PASS")?0:1;
  } catch(e) {
    report.status="INDEPENDENT_RECOMPILATION_FAILED";
    report.failure=String(e.message||e).slice(0,240);
    fs.writeFileSync(outputPath,JSON.stringify(report,null,2)+"\n");
    process.stderr.write(JSON.stringify({file:path.basename(inputPath),failure:report.failure})+"\n");
    return 1;
  }
}
if(require.main===module){
  if(process.argv.length!==5)process.exit(2);
  process.exit(run(process.argv[2],process.argv[3],process.argv[4]));
}
module.exports={checkedHex,applyImmutables};
