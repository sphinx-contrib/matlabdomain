function result = setSimulinkHelp(file, root, options)
%SETSIMULINKHELP Point the Help of Simulink objects to their documentation
%   result = sphinxcontrib.matlabdomain.setSimulinkHelp(file, root) sets
%   the Help of the objects that sphinxcontrib-matlabdomain documents in
%   the Simulink file file to a line that opens their page:
%
%       web(sphinxcontrib.matlabdomain.simulinkDocumentationLinker("<reference>"))
%
%   root is the project root of the documentation
%   (matlab_src_code_project_root); the path reference of file is its path
%   below root. The objects are:
%
%   - a model or subsystem file: the Help of its system mask (the mask of
%     the model itself);
%   - a library: the Help of the mask of each documented block, found as
%     the documentation finds them: every masked block at the top level,
%     and inside subsystems without a mask; linked blocks are skipped.
%
%   A Help that already has other text is left as it is. The file is
%   saved when a Help changed. result is a table with one row per object:
%   Reference, Block (the block path, "" for the file) and Action
%   ("set", "unchanged", "kept text" or "no mask").
%
%   result = sphinxcontrib.matlabdomain.setSimulinkHelp(___, Name=Value)
%   sets options:
%
%   Overwrite         - true replaces Help text that is not a link
%                       (default false).
%   CreateSystemMask  - true adds a system mask to a model or subsystem
%                       file without one (default false). A system mask
%                       changes the dialog of the Model blocks that
%                       reference the model.
%
%   See also sphinxcontrib.matlabdomain.simulinkDocumentationLinker,
%   Simulink.Mask.get.

arguments
    file (1,1) string {mustBeFile}
    root (1,1) string {mustBeFolder}
    options.Overwrite (1,1) logical = false
    options.CreateSystemMask (1,1) logical = false
end

reference = pathReference(file, root);
wasLoaded = bdIsLoaded(fileStem(file));
bd = load_system(file);
if ~wasLoaded
    closeOnExit = onCleanup(@() close_system(bd, 0));
end

rows = cell(0, 3);
if bdIsLibrary(bd)
    set_param(bd, "Lock", "off");
    for blk = documentedBlocks(bd, "")
        mask = Simulink.Mask.get(blk.handle);
        action = setHelp(mask, reference + "/" + blk.path, options.Overwrite);
        rows(end+1, :) = {reference + "/" + blk.path, blk.path, action}; %#ok<AGROW>
    end
else
    mask = Simulink.Mask.get(bd);
    if isempty(mask) && options.CreateSystemMask
        mask = Simulink.Mask.create(bd);
    end
    action = setHelp(mask, reference, options.Overwrite);
    rows(end+1, :) = {reference, "", action};
end
result = cell2table(rows, VariableNames=["Reference", "Block", "Action"]);
result.Reference = string(result.Reference);
result.Block = string(result.Block);
result.Action = string(result.Action);
if any(result.Action == "set")
    save_system(bd);
end
end

function action = setHelp(mask, reference, overwrite)
if isempty(mask)
    action = "no mask";
    return
end
line = helpLine(reference);
current = string(mask.Help);
if current == line
    action = "unchanged";
elseif strtrim(current) == "" || startsWith(strtrim(current), ...
        "web(sphinxcontrib.matlabdomain.simulinkDocumentationLinker(") || overwrite
    mask.Help = line;
    action = "set";
else
    action = "kept text";
end
end

function line = helpLine(reference)
% A MATLAB string literal of reference; a newline in a block name is
% written as newline.
literal = """" + replace(reference, """", """""") + """";
literal = replace(literal, newline, """ + newline + """);
line = "web(sphinxcontrib.matlabdomain.simulinkDocumentationLinker(" + literal + "))";
end

function blocks = documentedBlocks(system, prefix)
% The library walk of the documentation: masked blocks are documented and
% not entered, unmasked subsystems are entered, linked blocks are skipped.
blocks = struct("handle", {}, "path", {});
children = find_system(system, SearchDepth=1, LookUnderMasks="all", ...
    FollowLinks="off", Type="block");
for child = reshape(children, 1, [])
    if child == system || isempty(child)
        continue
    end
    name = replace(string(get_param(child, "Name")), "/", "//");
    path = name;
    if prefix ~= ""
        path = prefix + "/" + name;
    end
    if ismember(get_param(child, "LinkStatus"), ["resolved", "unresolved", "implicit"])
        continue
    end
    if ~isempty(Simulink.Mask.get(child))
        blocks(end+1) = struct("handle", child, "path", path); %#ok<AGROW>
    elseif get_param(child, "BlockType") == "SubSystem"
        blocks = [blocks, documentedBlocks(child, path)]; %#ok<AGROW>
    end
end
end

function reference = pathReference(file, root)
fileInfo = dir(file);
file = string(fullfile(fileInfo.folder, fileInfo.name));
rootInfo = dir(root);
root = string(rootInfo(1).folder);
if ~startsWith(file, root + filesep)
    error("sphinxcontrib:matlabdomain:outsideRoot", "%s is not below %s.", file, root);
end
reference = replace(extractAfter(file, strlength(root) + 1), filesep, "/");
end

function name = fileStem(file)
[~, name] = fileparts(file);
end
