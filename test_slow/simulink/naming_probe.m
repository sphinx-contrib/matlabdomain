function naming_probe(root)
%NAMING_PROBE Probe how MATLAB names and finds Simulink files.
%   naming_probe(root) creates small models below root (a new folder)
%   and prints one line per finding.
arguments
    root (1,1) string
end
if isfolder(root)
    rmdir(root, "s");
end
mkdir(root);
oldPath = path;
cleanup = onCleanup(@() restore(oldPath));
fprintf("release %s\n", version("-release"));

% 1 plain folder
p1 = mk(root, "p1");
makeModel(p1, "nm1", ".slx");
addpath(p1);
report("plain which", which("nm1"));
report("plain exist", exist("nm1")); %#ok<EXIST>
report("plain load", tryLoad("nm1"));

% 2 namespace folder
p2 = mk(root, "p2");
makeModel(mk(p2, "+pk"), "pkm", ".slx");
addpath(p2);
report("pkg which pk.pkm", which("pk.pkm"));
report("pkg which pkm", which("pkm"));
report("pkg load pk.pkm", tryLoad("pk.pkm"));
report("pkg load pkm", tryLoad("pkm"));
report("pkg load path", tryLoad(fullfile(p2, "+pk", "pkm.slx")));
% Loading pk.pkm works from R2026a; running or referencing it does not.
report("pkg sim pk.pkm", attempt(@() class(sim("pk.pkm"))));
top = new_system();
add_block("simulink/Ports & Subsystems/Model", get_param(top, "Name") + "/Ref");
report("pkg Model block pk.pkm", attempt(@() set_param( ...
    get_param(top, "Name") + "/Ref", "ModelName", "pk.pkm")));
close_system(top, 0);
bdclose("all");

% 3 private folder
p3 = mk(root, "p3");
privDir = mk(p3, "private");
makeModel(root, "prm", ".slx");
movefile(fullfile(root, "prm.slx"), privDir);
writelines(["function r = callprm"
    "r = string(which(""prm""));"
    "try"
    "    load_system(""prm""); r(2) = ""loaded"";"
    "    close_system(""prm"", 0);"
    "catch e"
    "    r(2) = e.identifier;"
    "end"], fullfile(p3, "callprm.m"));
addpath(p3);
report("private which (command line)", which("prm"));
r = callprm;
report("private which (from parent function)", r(1));
report("private load (from parent function)", r(2));
report("private load by path", tryLoad(fullfile(privDir, "prm.slx")));
report("private sim by path", attempt(@() class(sim(fullfile(privDir, "prm.slx")))));
report("private load (cd private)", inFolder(privDir, @() tryLoad("prm")));
report("private sim (cd private)", inFolder(privDir, @() attempt(@() class(sim("prm")))));
probeReferences("private", p3, privDir);

% 4 class folder
p4 = mk(root, "p4");
c4 = mk(p4, "@Ck");
writelines(["classdef Ck"
    "methods (Static)"
    "function r = loadSub"
    "try, load_system(""csm""); r = ""loaded""; close_system(""csm"", 0);"
    "catch e, r = e.identifier; end"
    "end"
    "function r = callSub"
    "try, r = string(feval(""csf"")); catch e, r = e.identifier; end"
    "end"
    "end"
    "end"], fullfile(c4, "Ck.m"));
makeModel(root, "ckm", ".slx");
movefile(fullfile(root, "ckm.slx"), c4);
addpath(p4);
report("class folder which ckm", which("ckm"));
report("class folder load ckm", tryLoad("ckm"));
report("class folder load path", tryLoad(fullfile(c4, "ckm.slx")));
report("class folder sim path", attempt(@() class(sim(fullfile(c4, "ckm.slx")))));
report("class folder load (cd)", inFolder(c4, @() tryLoad("ckm")));

% 4b subfolder of a class folder (.m files there callable before R2026a)
s4 = mk(c4, "sub");
makeModel(root, "csm", ".slx");
movefile(fullfile(root, "csm.slx"), s4);
writelines(["function r = csf", "r = ""m in class subfolder"";"], fullfile(s4, "csf.m"));
rehash;
report("class subfolder which csf.m", which("csf"));
report("class subfolder call csf.m (method)", Ck.callSub());
report("class subfolder which csm", which("csm"));
report("class subfolder load csm", tryLoad("csm"));
report("class subfolder load csm (method)", Ck.loadSub());
report("class subfolder load path", tryLoad(fullfile(s4, "csm.slx")));
report("class subfolder sim path", attempt(@() class(sim(fullfile(s4, "csm.slx")))));
report("class subfolder load (cd)", inFolder(s4, @() tryLoad("csm")));
probeReferences("class subfolder", p4, s4);
report("class subfolder addpath", attempt(@() addpath(s4)));
report("class subfolder load csm (on path)", tryLoad("csm"));
report("class subfolder which csf.m (on path)", which("csf"));
report("class subfolder call csf.m (on path)", attempt(@() feval("csf")));
rmpath(s4);

% 4c deeper: does Simulink check only the file's own folder?
for rel = ["private/deep", "@Ck/sub/deep", "@Ck/private", "+pk/@Ck2/deep"]
    folder = fullfile(p4, rel);
    mkdir(folder);
    makeModel(root, "dm", ".slx");
    movefile(fullfile(root, "dm.slx"), folder);
    report("load by path " + rel + "/dm.slx", tryLoad(fullfile(folder, "dm.slx")));
end

% 5 .slx and .mdl with one name
p5 = mk(root, "p5");
makeModel(p5, "dup", ".mdl");
makeModel(p5, "dup", ".slx");
addpath(p5);
report("slx+mdl which", which("dup"));
report("slx+mdl which -all", strjoin(string(which("dup", "-all")), " | "));
lastwarn("");
report("slx+mdl load", tryLoad("dup"));
[msg, id] = lastwarn;
report("slx+mdl warning", id + " " + msg);

% 6 .m and .slx with one name
p6 = mk(root, "p6");
makeModel(p6, "both", ".slx");
writelines(["function r = both", "r = ""m file"";"], fullfile(p6, "both.m"));
addpath(p6);
report(".m+.slx which", which("both"));
report(".m+.slx which -all", strjoin(string(which("both", "-all")), " | "));
report(".m+.slx exist", exist("both")); %#ok<EXIST>
try
    report(".m+.slx call", both());
catch e
    report(".m+.slx call", e.identifier);
end
report(".m+.slx load", tryLoad("both"));

% 7 name length
p7 = mk(root, "p7");
for n = [63 64 100]
    name = "L" + string(repmat('x', 1, n - 1));
    try
        makeModel(p7, name, ".slx");
        report("length " + n, "saved");
    catch e
        report("length " + n, e.identifier + " " + e.message);
    end
end

% 8 names that are not identifiers
p8 = mk(root, "p8");
makeModel(p8, "okname", ".slx");
copyfile(fullfile(p8, "okname.slx"), fullfile(p8, "bad-name.slx"));
report("bad-name load by path", tryLoad(fullfile(p8, "bad-name.slx")));
try
    new_system("end");
    report("new_system end", "created");
    close_system("end", 0);
catch e
    report("new_system end", e.identifier);
end

% 9 .mlapp-like precedence with .p? and .slx vs .mlx
p9 = mk(root, "p9");
makeModel(p9, "lv", ".slx");
writelines(["function r = lv", "r = 1;"], fullfile(p9, "lv.m"));
pcode(fullfile(p9, "lv.m"), "-inplace");
delete(fullfile(p9, "lv.m"));
addpath(p9);
report(".p+.slx which", which("lv"));
end

function report(what, value)
fprintf("%-40s %s\n", what, string(value));
end

function folder = mk(parent, name)
folder = fullfile(parent, name);
mkdir(folder);
end

function makeModel(folder, name, ext)
h = new_system();
set_param(h, "Description", name + ext);
model = get_param(h, "Name");
add_block("simulink/Sources/Constant", model + "/C");
add_block("simulink/Sinks/Terminator", model + "/T");
add_line(model, "C/1", "T/1");
save_system(h, fullfile(folder, name + ext));
close_system(h, 0);
end

function out = attempt(f)
try
    f();
    out = "ok";
catch e
    out = "error " + e.identifier;
end
end

function out = inFolder(folder, f)
old = cd(folder);
back = onCleanup(@() cd(old));
out = f();
end

function probeReferences(label, parent, hidden)
% A model in parent (on the path) refers to files in hidden: a Model block,
% a Subsystem Reference block and a library link. Simulink saves nothing in
% hidden, so the files are made in parent, referenced, then moved.
bdclose("all");
tag = matlab.lang.makeValidName(label);
ref = tag + "Ref";
sub = tag + "Sub";
lib = tag + "Lib";
makeModel(parent, ref, ".slx");
h = new_system(sub, "Subsystem");
add_block("simulink/Sources/Constant", sub + "/C");
add_block("simulink/Sinks/Out1", sub + "/O");
add_line(sub, "C/1", "O/1");
save_system(h, fullfile(parent, sub + ".slx"));
close_system(h, 0);
h = new_system(lib, "Library");
add_block("simulink/Sources/Constant", lib + "/K");
% Only masked blocks and subsystems become library links.
set_param(lib + "/K", "Mask", "on");
save_system(h, fullfile(parent, lib + ".slx"));

tops = [tag + "TopRef", tag + "TopSub", tag + "TopLib"];
for top = tops
    new_system(top);
end
add_block("simulink/Ports & Subsystems/Model", tops(1) + "/M");
report(label + " Model block set", attempt(@() set_param(tops(1) + "/M", "ModelName", ref)));
add_block("simulink/Ports & Subsystems/Subsystem Reference", tops(2) + "/S");
report(label + " Subsystem Reference set", ...
    attempt(@() set_param(tops(2) + "/S", "ReferencedSubsystem", sub)));
add_block(lib + "/K", tops(3) + "/K");
add_block("simulink/Sinks/Terminator", tops(3) + "/T");
add_line(tops(3), "K/1", "T/1");
for top = tops
    save_system(top, fullfile(parent, top + ".slx"));
    report(label + " " + top + " update (before move)", ...
        attempt(@() set_param(top, "SimulationCommand", "update")));
end
bdclose("all");
for name = [ref, sub, lib]
    movefile(fullfile(parent, name + ".slx"), hidden);
end
rehash;
for top = tops
    report(label + " " + top + " update", attempt(@() updateModel(top)));
    bdclose("all");
end
load_system(tops(3));
report(label + " library link status", get_param(tops(3) + "/K", "LinkStatus"));
bdclose("all");
end

function updateModel(top)
load_system(top);
set_param(top, "SimulationCommand", "update");
end

function out = tryLoad(name)
try
    h = load_system(name);
    out = "loaded " + string(get_param(h, "Name")) + " " + string(get_param(h, "FileName"));
    close_system(h, 0);
catch e
    out = "error " + e.identifier;
end
end

function restore(oldPath)
path(oldPath);
bdclose("all");
clear("Ck");
end
