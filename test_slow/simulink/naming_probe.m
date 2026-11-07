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

% 4 class folder
p4 = mk(root, "p4");
c4 = mk(p4, "@Ck");
writelines(["classdef Ck", "end"], fullfile(c4, "Ck.m"));
makeModel(root, "ckm", ".slx");
movefile(fullfile(root, "ckm.slx"), c4);
addpath(p4);
report("class folder which ckm", which("ckm"));
report("class folder load ckm", tryLoad("ckm"));
report("class folder load path", tryLoad(fullfile(c4, "ckm.slx")));

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
save_system(h, fullfile(folder, name + ext));
close_system(h, 0);
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
end
