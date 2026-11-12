function make_fixtures(step, outDir)
%MAKE_FIXTURES Write the Simulink test fixtures and their oracle.
%   make_fixtures("sources", outDir) builds the probe diagrams (model,
%   referenced model, library, subsystem file) in the running release and
%   saves them in outDir/<release>/slx.
%
%   make_fixtures("export", outDir) saves the sources of the running
%   release to every release in FIXTURE_RELEASES, as .slx (from R2012a)
%   and .mdl, below outDir/<release>/{slx,mdl}.
%
%   make_fixtures("native", outDir) builds the sources in the running
%   release and saves them in outDir/<release>-native/slx.
%
%   make_fixtures("oracle", outDir) loads every fixture below outDir and
%   writes what the Simulink API reports to outDir/../oracle.json.
%
%   make_fixtures("linker", outDir) writes the addresses that
%   sphinxcontrib.matlabdomain.simulinkDocumentationLinker gives for some
%   path references to outDir/../linker.json (any release).
%
%   Run "sources", "export" and "oracle" in R2026b, and "native" in R2024a.
%   Creator and modifier are set to "matlabdomain", so no user name is
%   saved in the files.

arguments
    step (1,1) string {mustBeMember(step, ["sources", "export", "native", "oracle", "linker"])}
    outDir (1,1) string
end

switch step
    case "sources"
        makeSources(fullfile(outDir, currentRelease(), "slx"), ".slx");
    case "export"
        exportAll(fullfile(outDir, currentRelease(), "slx"), outDir);
    case "native"
        makeSources(fullfile(outDir, currentRelease() + "-native", "slx"), ".slx");
    case "oracle"
        writeOracle(outDir);
    case "linker"
        writeLinker(outDir);
end
end

function writeLinker(outDir)
references = ["./", "src/", "src/+pkg/@Cls/", "src/f.m", "src/+pkg/Cls.m.method", ...
    "my folder/données.m", "CON.m", "aux/Lpt1.txt.m", "src/trail.", "src/a~b.m", ...
    "src/lib.slx", "src/lib.slx/Group/Inner Masked", "src/lib.slx/A//B", ...
    "src/lib.slx/Two" + newline + "Lines", "src/lib.mdl/Größe", ...
    "lib.slx/x", "src/x.slx.d/f.m", "src/M.SLX/x.m", "src/.slx/f.m", ...
    "_u/lib.slx/G", "src/_pkg/_inner/f.m", "src/_x/lib.slx/Group/Gain", "_u/", ...
    "src/_u/", "_f.m", "src/_f.m", "_u/_f.m"];
source = fullfile(fileparts(mfilename("fullpath")), "..", "..", "sphinxcontrib", ...
    "mat_simulink", "matlab");
scratch = tempname;
copyfile(source, scratch);
base = "https://example.org/docs/";
writelines(jsonencode(struct("mode", "published", "published", base)), ...
    fullfile(scratch, "+sphinxcontrib", "+matlabdomain", "simulinkDocumentationLinker.json"));
oldPath = addpath(scratch);
cleanup = onCleanup(@() removeScratch(oldPath, scratch));
clear("sphinxcontrib.matlabdomain.simulinkDocumentationLinker");
cases = struct("reference", {}, "address", {});
for reference = references
    url = sphinxcontrib.matlabdomain.simulinkDocumentationLinker(reference);
    cases(end+1) = struct("reference", reference, "address", extractAfter(url, base)); %#ok<AGROW>
end
text = jsonencode(struct("generatedBy", currentRelease(), "cases", cases), ...
    "PrettyPrint", true);
writelines(text, fullfile(outDir, "..", "linker.json"), "Encoding", "UTF-8");
end

function removeScratch(oldPath, scratch)
path(oldPath);
rmdir(scratch, "s");
end

function releases = fixtureReleases()
% One release per format change point (developer guide, file formats).
releases = ["R2006a", "R2012a", "R2015a", "R2015b", "R2017a", "R2017b", ...
    "R2019b", "R2020a", "R2021a", "R2026a"];
end

function name = currentRelease()
name = "R" + string(version("-release"));
end

function names = diagramNames()
names = ["probeLib", "probeSub", "probeRef", "probeModel"];
end

function makeSources(srcDir, extension)
if ~isfolder(srcDir), mkdir(srcDir); end
oldDir = cd(srcDir);
restoreDir = onCleanup(@() cd(oldDir));
bdclose("all");
for name = diagramNames()
    target = fullfile(srcDir, name + extension);
    if isfile(target), delete(target); end
end

lib = "probeLib";
new_system(lib, "Library");
set_param(lib, "Description", "Library description");
addMasked(lib + "/Gain Block", "GainType", "Top masked block description.", "Top masked help.");
add_block("simulink/Ports & Subsystems/Subsystem", lib + "/Group");
set_param(lib + "/Group", "Description", "Unmasked group description");
addMasked(lib + "/Group/Inner Masked", "InnerType", "Inner masked description.", "Inner help.");
add_block("simulink/Ports & Subsystems/Subsystem", lib + "/Group/Deeper");
addMasked(lib + "/Group/Deeper/Deep Masked", "DeepType", "Deep masked description.", "");
add_block("simulink/Math Operations/Gain", lib + "/Group/Plain Gain");
addMasked(lib + "/Two" + newline + "Lines", "NewlineType", "Name has a newline.", "");
addMasked(lib + "/A//B", "SlashType", "Name has a slash.", "");
addMasked(lib + "/v1.2", "DotType", "Name has a dot.", "");
addMasked(lib + "/Größe", "UnicodeType", "Name is non-ASCII: Größe.", "");
addMasked(lib + "/No Description", "", "", "");
add_block("simulink/Sinks/Scope", lib + "/Linked Scope");
add_block("simulink/Model-Wide Utilities/DocBlock", lib + "/Lib Doc");
setDoc(lib + "/Lib Doc", "Text", "Library DocBlock text.");
saveSanitized(lib, fullfile(srcDir, lib + extension));
close_system(lib);

sub = "probeSub";
new_system(sub, "Subsystem");
set_param(sub, "Description", "Subsystem file description");
add_block("simulink/Sources/In1", sub + "/in");
set_param(sub + "/in", "Description", "sub input doc", "OutDataTypeStr", "single");
add_block("simulink/Sinks/Out1", sub + "/out");
add_line(sub, "in/1", "out/1");
mask = Simulink.Mask.create(sub);
mask.Type = "SubFileMaskType";
mask.Description = "Subsystem file mask description";
mask.Help = "Subsystem file mask help";
mask.addParameter("Name", "k", "Prompt", "Factor k", "Value", "1");
saveSanitized(sub, fullfile(srcDir, sub + extension));
close_system(sub);

ref = "probeRef";
new_system(ref);
set_param(ref, "Description", "Referenced model description");
add_block("simulink/Sources/In1", ref + "/ri");
add_block("simulink/Sinks/Out1", ref + "/ro");
add_line(ref, "ri/1", "ro/1");
saveSanitized(ref, fullfile(srcDir, ref + extension));
close_system(ref);

mdl = "probeModel";
new_system(mdl);
set_param(mdl, "Description", "Model description line 1" + newline + "line 2");
add_block("simulink/Sources/In1", mdl + "/u");
set_param(mdl + "/u", "Description", "input u doc", "OutDataTypeStr", "double", ...
    "PortDimensions", "3", "Unit", "m");
add_block("simulink/Sources/In1", mdl + "/w");
set_param(mdl + "/w", "Port", "2", "Description", "second input");
add_block("simulink/Sinks/Out1", mdl + "/y");
set_param(mdl + "/y", "Description", "output y doc");
add_block("simulink/Ports & Subsystems/In Bus Element", mdl + "/BusIn");
set_param(mdl + "/BusIn", "PortName", "busPort", "Element", "sig1");
addMasked(mdl + "/Masked Sub", "ModelMaskType", "Masked subsystem in model.", "Masked help in model.");
add_block("simulink/Ports & Subsystems/Subsystem", mdl + "/Plain Sub");
set_param(mdl + "/Plain Sub", "Description", "Plain subsystem description");
add_block("simulink/Model-Wide Utilities/DocBlock", mdl + "/Doc Text");
setDoc(mdl + "/Doc Text", "Text", "DocBlock text content.");
add_block("simulink/Ports & Subsystems/Subsystem Reference", mdl + "/SubRef");
set_param(mdl + "/SubRef", "ReferencedSubsystem", sub);
add_block("simulink/Ports & Subsystems/Model", mdl + "/MdlRef");
set_param(mdl + "/MdlRef", "ModelName", ref);
load_system(fullfile(srcDir, lib + extension));
add_block(lib + "/Gain Block", mdl + "/Linked Gain");
close_system(lib);
add_block("simulink/Ports & Subsystems/Variant Subsystem", mdl + "/Variants");
note = Simulink.Annotation(mdl + "/note");
note.Text = "Annotation text";
mask = Simulink.Mask.create(mdl);
mask.Type = "ModelMaskType";
mask.Description = "Model mask description";
mask.Help = "Model mask help";
saveSanitized(mdl, fullfile(srcDir, mdl + extension));
close_system(mdl, 0);
end

function addMasked(path, maskType, description, help)
add_block("simulink/Ports & Subsystems/Subsystem", path);
mask = Simulink.Mask.create(path);
mask.Type = maskType;
mask.Description = description;
mask.Help = help;
mask.addParameter("Name", "gain", "Prompt", "Gain value", "Value", "2", "Type", "edit");
mask.addParameter("Name", "mode", "Prompt", "Mode", "Type", "popup", ...
    "TypeOptions", ["fast", "slow"], "Value", "fast");
mask.addParameter("Name", "flag", "Prompt", "Enable", "Type", "checkbox", "Value", "on");
end

function setDoc(path, docType, content)
set_param(path, "DocumentType", docType);
% char, not string: a string is saved as an opaque class object.
set_param(path, "UserData", struct("version", 1.1, "content", char(content)), ...
    "UserDataPersistent", "on");
end

function saveSanitized(name, target, varargin)
if bdIsLibrary(name), set_param(name, "Lock", "off"); end
set_param(name, "Creator", "matlabdomain", "ModifiedByFormat", "matlabdomain");
save_system(name, target, varargin{:});
end

function exportAll(srcDir, outDir)
addpath(srcDir);
restorePath = onCleanup(@() rmpath(srcDir));
bdclose("all");
for name = diagramNames()
    load_system(fullfile(srcDir, name + ".slx"));
    for release = fixtureReleases()
        if name == "probeSub" && release < "R2019b", continue; end
        targets = fullfile(outDir, release, "mdl", name + ".mdl");
        if release >= "R2012a"
            targets(end+1) = fullfile(outDir, release, "slx", name + ".slx"); %#ok<AGROW>
        end
        for target = targets
            folder = fileparts(target);
            if ~isfolder(folder), mkdir(folder); end
            evalc("saveSanitized(name, target, ""ExportToVersion"", release)");
        end
    end
    close_system(name, 0);
end
end

function writeOracle(outDir)
files = [dir(fullfile(outDir, "**", "*.slx")); dir(fullfile(outDir, "**", "*.mdl"))];
entries = struct("file", {}, "facts", {});
bdclose("all");
warnState = warning("off", "all");
restoreWarn = onCleanup(@() warning(warnState));
for k = 1:numel(files)
    file = string(fullfile(files(k).folder, files(k).name));
    relative = extractAfter(replace(file, "\", "/"), replace(outDir, "\", "/") + "/");
    folder = string(files(k).folder);
    addpath(folder);
    name = string(get_param(load_system(file), "Name"));
    entries(end+1) = struct("file", relative, "facts", diagramFacts(name, file)); %#ok<AGROW>
    close_system(name, 0);
    rmpath(folder);
end
oracle = struct("generatedBy", currentRelease(), "fixtures", entries);
text = jsonencode(oracle, "PrettyPrint", true);
writelines(text, fullfile(outDir, "..", "oracle.json"), "Encoding", "UTF-8");
end

function facts = diagramFacts(name, file)
info = Simulink.MDLInfo(file);
facts.kind = lower(string(get_param(name, "BlockDiagramType")));
facts.description = string(get_param(name, "Description"));
facts.release = string(info.ReleaseName);
facts.systemMask = maskFacts(Simulink.Mask.get(name));
facts.ports = portFacts(name);
facts.references = referenceFacts(name);
if facts.kind == "library"
    facts.libraryBlocks = libraryWalk(name, name);
else
    facts.libraryBlocks = struct([]);
end
end

function facts = maskFacts(mask)
if isempty(mask)
    facts = struct([]);
    return
end
parameters = struct("name", {}, "prompt", {}, "type", {}, "value", {});
for p = mask.Parameters
    parameters(end+1) = struct("name", string(p.Name), "prompt", string(p.Prompt), ...
        "type", string(p.Type), "value", string(p.Value)); %#ok<AGROW>
end
facts = struct("type", string(mask.Type), "description", string(mask.Description), ...
    "help", string(mask.Help), "parameters", parameters);
end

function ports = portFacts(system)
ports = struct("blockType", {}, "name", {}, "port", {}, "dataType", {}, ...
    "dimensions", {}, "unit", {}, "description", {}, "portName", {}, "element", {});
for blockType = ["Inport", "Outport", "PMIOPort"]
    blocks = find_system(system, "SearchDepth", 1, "BlockType", blockType);
    for b = string(blocks)'
        dataType = ""; dimensions = ""; unit = ""; portName = ""; element = "";
        if blockType ~= "PMIOPort"
            dataType = string(get_param(b, "OutDataTypeStr"));
            dimensions = string(get_param(b, "PortDimensions"));
            unit = string(get_param(b, "Unit"));
            if get_param(b, "IsBusElementPort") == "on"
                portName = string(get_param(b, "PortName"));
                element = string(get_param(b, "Element"));
            end
        end
        ports(end+1) = struct("blockType", blockType, "name", string(get_param(b, "Name")), ...
            "port", string(get_param(b, "Port")), "dataType", dataType, ...
            "dimensions", dimensions, "unit", unit, ...
            "description", string(get_param(b, "Description")), ...
            "portName", portName, "element", element); %#ok<AGROW>
    end
end
end

function refs = referenceFacts(system)
refs = struct("kind", {}, "block", {}, "target", {});
options = {"LookUnderMasks", "all", "FollowLinks", "off", ...
    "MatchFilter", @Simulink.match.allVariants};
for b = string(find_system(system, options{:}, "BlockType", "ModelReference"))'
    refs(end+1) = struct("kind", "model", "block", blockPath(b, system), ...
        "target", string(get_param(b, "ModelNameDialog"))); %#ok<AGROW>
end
for b = string(find_system(system, options{:}, "BlockType", "SubSystem"))'
    target = string(get_param(b, "ReferencedSubsystem"));
    if target ~= ""
        refs(end+1) = struct("kind", "subsystem", "block", blockPath(b, system), ...
            "target", target); %#ok<AGROW>
    end
end
for b = string(find_system(system, options{:}, "LinkStatus", "resolved"))'
    refs(end+1) = struct("kind", "library", "block", blockPath(b, system), ...
        "target", string(get_param(b, "ReferenceBlock"))); %#ok<AGROW>
end
end

function blocks = libraryWalk(system, library)
% Library walk: a linked block is a link; a masked block is documented and
% not entered; an unmasked subsystem is entered.
blocks = struct("path", {}, "link", {}, "mask", {}, "description", {});
children = string(find_system(system, "SearchDepth", 1, "LookUnderMasks", "all", ...
    "FollowLinks", "off", "Type", "block"));
for b = children(children ~= system)'
    path = blockPath(b, library);
    if get_param(b, "LinkStatus") ~= "none"
        blocks(end+1) = struct("path", path, "link", string(get_param(b, "ReferenceBlock")), ...
            "mask", struct([]), "description", string(get_param(b, "Description"))); %#ok<AGROW>
    elseif ~isempty(Simulink.Mask.get(b))
        blocks(end+1) = struct("path", path, "link", "", ...
            "mask", maskFacts(Simulink.Mask.get(b)), ...
            "description", string(get_param(b, "Description"))); %#ok<AGROW>
    elseif get_param(b, "BlockType") == "SubSystem"
        blocks = [blocks, libraryWalk(b, library)]; %#ok<AGROW>
    end
end
end

function path = blockPath(block, system)
% Path below the diagram, as Simulink writes it: "/" in a name is "//".
names = strings(0);
current = string(block);
while current ~= string(system) && current ~= ""
    names = [replace(string(get_param(current, "Name")), "/", "//"), names]; %#ok<AGROW>
    current = string(get_param(current, "Parent"));
end
path = strjoin(names, "/");
end
