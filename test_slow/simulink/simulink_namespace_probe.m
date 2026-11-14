function simulink_namespace_probe(root)
%SIMULINK_NAMESPACE_PROBE What works for Simulink files in namespace folders.
%   simulink_namespace_probe(root) makes small models, subsystem files and
%   libraries (.slx and .mdl) in root/parent/+pk and +pk/+inner, with
%   root/parent on the path, and prints one line per check. Needs Simulink
%   only; root defaults to a folder below tempdir.
arguments
    root (1,1) string = fullfile(tempdir, "simulink_namespace_probe")
end
if isfolder(root)
    rmdir(root, "s");
end
parent = fullfile(root, "parent");
pk = fullfile(parent, "+pk");
inner = fullfile(pk, "+inner");
mkdir(inner);
oldPath = addpath(parent);
oldDir = pwd;
cleanup = onCleanup(@() restore(oldPath, oldDir));
warning("off", "all");
fprintf("MATLAB %s\n", version("-release"));
for ext = [".slx", ".mdl"]
    tag = extractAfter(ext, 1);
    m = "nm_" + tag;
    sub = "ns_" + tag;
    lib = "nl_" + tag;
    deep = "nd_" + tag;
    makeModel(pk, m, ext);
    makeSub(pk, sub, ext);
    makeLib(pk, lib, ext);
    makeModel(inner, deep, ext);
    rehash;
    q = "pk." + m;
    file = fullfile(pk, m + ext);
    fprintf("\n--- %s in +pk (model %s) ---\n", ext, q);
    show("which " + q, which(q));
    show("which " + m + " (short name)", which(m));
    show("exist " + q, string(exist(q))); %#ok<EXIST>
    show("load_system " + q, loadName(q));
    show("sim " + q, attempt(@() sim(q)));
    show("load_system " + q + ", then sim " + m, attempt(@() loadThenSim(q, m)));
    show("load_system by full path", loadName(file));
    show("load_system by full path, then sim " + m, attempt(@() loadThenSim(file, m)));
    show("sim by full path", attempt(@() sim(file)));
    show("sim " + m + " (short name, not loaded)", attempt(@() sim(m)));
    show("cd +pk, then load_system " + m, inFolder(pk, @() loadName(m)));
    show("cd +pk, then sim " + m, inFolder(pk, @() attempt(@() sim(m))));
    show("which pk.inner." + deep, which("pk.inner." + deep));
    show("load_system pk.inner." + deep, loadName("pk.inner." + deep));
    show("sim pk.inner." + deep, attempt(@() sim("pk.inner." + deep)));
    show("sim pk.inner." + deep + " by full path", ...
        attempt(@() sim(fullfile(inner, deep + ext))));
    for target = [q, m]
        show("Model block, ModelName " + target, ...
            refModel(parent, "topM_" + tag, target, ext, file));
    end
    for target = ["pk." + sub, sub]
        show("Subsystem Reference, ReferencedSubsystem " + target, ...
            refSub(parent, "topS_" + tag, target, ext, fullfile(pk, sub + ext)));
    end
    show("library link from pk." + lib + " (loaded by qualified name)", ...
        refLib(parent, "topL_" + tag, "pk." + lib, lib, ext));
    show("library link from " + lib + " (loaded by full path)", ...
        refLib(parent, "topP_" + tag, fullfile(pk, lib + ext), lib, ext));
end
end

function makeModel(folder, name, ext)
h = new_system(name);
add_block("simulink/Sources/Constant", name + "/C");
add_block("simulink/Sinks/Terminator", name + "/T");
add_line(name, "C/1", "T/1");
save_system(h, fullfile(folder, name + ext));
close_system(h, 0);
end

function makeSub(folder, name, ext)
h = new_system(name, "Subsystem");
add_block("simulink/Sources/Constant", name + "/C");
add_block("simulink/Sinks/Out1", name + "/O");
add_line(name, "C/1", "O/1");
save_system(h, fullfile(folder, name + ext));
close_system(h, 0);
end

function makeLib(folder, name, ext)
h = new_system(name, "Library");
add_block("simulink/Sources/Constant", name + "/K");
set_param(name + "/K", "Mask", "on"); % unmasked blocks do not link
save_system(h, fullfile(folder, name + ext));
close_system(h, 0);
end

function out = loadName(what)
try
    h = load_system(what);
    out = "ok, loaded as " + string(get_param(h, "Name"));
catch e
    out = "error " + e.identifier;
end
bdclose("all");
end

function loadThenSim(what, name)
load_system(what);
sim(name);
end

function out = refModel(parent, top, target, ext, targetFile)
new_system(top);
add_block("simulink/Ports & Subsystems/Model", top + "/M");
try
    set_param(top + "/M", "ModelName", target);
catch e
    bdclose("all");
    out = "set ModelName: error " + e.identifier;
    return
end
save_system(top, fullfile(parent, top + ext));
bdclose("all");
out = "set ok; sim of parent model: " + attempt(@() sim(top)) + ...
    "; with the target loaded by full path first: " + attempt(@() loadThenSim(targetFile, top));
end

function out = refSub(parent, top, target, ext, targetFile)
new_system(top);
add_block("simulink/Ports & Subsystems/Subsystem Reference", top + "/S");
try
    set_param(top + "/S", "ReferencedSubsystem", target);
catch e
    bdclose("all");
    out = "set ReferencedSubsystem: error " + e.identifier;
    return
end
add_block("simulink/Sinks/Terminator", top + "/T");
try
    add_line(top, "S/1", "T/1");
catch
end
save_system(top, fullfile(parent, top + ext));
bdclose("all");
out = "set ok; sim of parent model: " + attempt(@() sim(top)) + ...
    "; with the target loaded by full path first: " + attempt(@() loadThenSim(targetFile, top));
end

function out = refLib(parent, top, loadWith, lib, ext)
try
    load_system(loadWith);
    new_system(top);
    add_block(lib + "/K", top + "/K");
    add_block("simulink/Sinks/Terminator", top + "/T");
    add_line(top, "K/1", "T/1");
    save_system(top, fullfile(parent, top + ext));
catch e
    bdclose("all");
    out = "make link: error " + e.identifier;
    return
end
bdclose("all");
out = "link ok; sim of parent model: " + attempt(@() sim(top)) + ...
    "; with the library loaded first: " + attempt(@() loadThenSim(loadWith, top));
end

function out = inFolder(folder, f)
old = cd(folder);
back = onCleanup(@() cd(old));
out = f();
bdclose("all");
end

function out = attempt(f)
try
    f();
    out = "ok";
catch e
    out = "error " + e.identifier;
end
bdclose("all");
end

function show(what, value)
if value == ""
    value = "(empty)";
end
fprintf("%-62s %s\n", what, value);
end

function restore(oldPath, oldDir)
cd(oldDir);
path(oldPath);
bdclose("all");
end
