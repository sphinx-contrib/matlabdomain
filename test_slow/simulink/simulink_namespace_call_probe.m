function simulink_namespace_call_probe(root)
%SIMULINK_NAMESPACE_CALL_PROBE The namespace name used as an expression.
%   Checks sim(pk.nm) and sim() of the nested model without quotes, and what the
%   expression pk.nm returns, for .slx and .mdl files.
arguments
    root (1,1) string = fullfile(tempdir, "simulink_namespace_call_probe")
end
if isfolder(root)
    rmdir(root, "s");
end
parent = fullfile(root, "parent");
inner = fullfile(parent, "+pk", "+inner");
mkdir(inner);
oldPath = addpath(parent);
cleanup = onCleanup(@() restore(oldPath));
warning("off", "all");
fprintf("MATLAB %s\n", version("-release"));
for ext = [".slx", ".mdl"]
    tag = extractAfter(ext, 1);
    makeModel(fullfile(parent, "+pk"), "nm_" + tag, ext);
    makeModel(inner, "nd_" + tag, ext);
    rehash;
    for q = ["pk.nm_" + tag, "pk.inner.nd_" + tag]
        try
            r = describe(eval(q));
        catch e
            r = "error " + e.identifier + ": " + e.message;
        end
        show(q + " (expression)", r);
        show("loaded after the expression", ...
            strjoin(string(find_system("type", "block_diagram")), ","));
        bdclose("all");
        show("sim(" + q + ") (no quotes)", attempt(@() class(eval("sim(" + q + ")"))));
        show("feval(""" + q + """)", attempt(@() describe(feval(q))));
        bdclose("all");
    end
end
end

function out = describe(value)
out = "returns " + class(value) + " " + strjoin(string(value), ",");
end

function makeModel(folder, name, ext)
h = new_system(name);
add_block("simulink/Sources/Constant", name + "/C");
add_block("simulink/Sinks/Terminator", name + "/T");
add_line(name, "C/1", "T/1");
save_system(h, fullfile(folder, name + ext));
close_system(h, 0);
end

function out = attempt(f)
try
    out = string(f());
catch e
    out = "error " + e.identifier + ": " + e.message;
end
bdclose("all");
end

function show(what, value)
if value == ""
    value = "(empty)";
end
fprintf("%-44s %s\n", what, value);
end

function restore(oldPath)
path(oldPath);
bdclose("all");
end
