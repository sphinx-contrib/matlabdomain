function url = simulinkDocumentationLinker(reference)
%SIMULINKDOCUMENTATIONLINKER Address of the documentation page of a Simulink object
%   url = sphinxcontrib.matlabdomain.simulinkDocumentationLinker(reference)
%   returns the address of the page that documents the object with the
%   path reference reference in a site built by sphinxcontrib-matlabdomain:
%   a model, library or subsystem file ("src/plant.slx") or a block of a
%   library ("src/lib.slx/Group/Gain", a / in a block name doubled).
%
%   Use it in the Help of a model, subsystem file or library block, so
%   that the Help button opens the page:
%
%       web(sphinxcontrib.matlabdomain.simulinkDocumentationLinker("src/lib.slx/Gain"))
%
%   simulinkDocumentationLinker.json, next to this file, names the sites;
%   scmd quickstart writes it; edit "local", "server" and "published" when
%   the setup changes (an HTML build says when they differ from the build):
%
%       {"mode": "local",
%        "local": "docs/_build/html/",
%        "server": "http://127.0.0.1:8000/",
%        "published": "https://example.org/docs/"}
%
%   "local" is a folder relative to the folder that holds +sphinxcontrib
%   (the project root), opened as a file:// address; a value with "://"
%   is used as it is.
%
%   The mode is, first that is set: the preference
%   getpref("sphinxcontrib_matlabdomain", "linkerMode") (one person's
%   choice; rmpref removes it), the last build (each HTML build writes
%   mat/simulinkDocumentationLinker.json in "local": "local" after make
%   html, "server" after make livehtml), "mode" above. A site that is not
%   there gives way: server (not running), then the local build (not
%   built), then the published site. The files are read on every call,
%   so switching sites changes no model.
%
%   The address is the object's stable address (mat/ref/...). It cannot
%   know the other files of the project, so it does not follow the rules
%   that depend on siblings: names that differ only by case (files,
%   folders, blocks, class members) and a folder named like the page file
%   of a sibling (guide-md.rst/); those pages get other addresses.
%
%   See also web, sphinxcontrib.matlabdomain.setSimulinkHelp, setpref.

arguments
    reference (1,1) string
end
url = baseUrl() + "mat/ref/" + stablePath(reference) + ".html";
end

function base = baseUrl()
folder = fileparts(mfilename("fullpath"));
projectRoot = fileparts(fileparts(folder));
file = fullfile(folder, "simulinkDocumentationLinker.json");
if ~isfile(file)
    error("sphinxcontrib:matlabdomain:noSettings", ...
        "No settings file %s; scmd quickstart writes it.", file);
end
settings = jsondecode(fileread(file));
modes = ["local", "server", "published"];
mode = textField(settings, "mode", "local");
local = textField(settings, "local", "");
state = [];
if local ~= "" && ~contains(local, "://")
    stateFile = fullfile(projectRoot, local, "mat", "simulinkDocumentationLinker.json");
    if isfile(stateFile)
        try
            state = jsondecode(fileread(stateFile));
            mode = textField(state, "mode", mode);
        catch
            state = [];
        end
    end
end
source = file;
if ispref("sphinxcontrib_matlabdomain", "linkerMode")
    mode = string(getpref("sphinxcontrib_matlabdomain", "linkerMode"));
    source = "getpref(""sphinxcontrib_matlabdomain"", ""linkerMode"")";
end
if ~isscalar(mode) || ~ismember(mode, modes)
    error("sphinxcontrib:matlabdomain:badSettings", ...
        "%s: the mode must be ""local"", ""server"" or ""published"".", source);
end
switch mode
    case "server"
        order = ["server", "local", "published"];
    case "local"
        order = ["local", "published"];
    otherwise
        order = ["published", "local"];
end
for site = order
    switch site
        case "server"
            server = textField(state, "server", ...
                textField(settings, "server", "http://127.0.0.1:8000/"));
            base = withSlash(server);
            if isServing(base)
                return
            end
        case "local"
            if local == ""
                continue
            end
            base = siteUrl(local, projectRoot);
            if contains(local, "://") || isfolder(fullfile(projectRoot, local, "mat"))
                return
            end
        case "published"
            published = textField(settings, "published", "");
            if published ~= ""
                base = withSlash(published);
                return
            end
    end
end
error("sphinxcontrib:matlabdomain:noSite", ...
    "No documentation site: build it (make html in the docs folder) or " + ...
    "set ""published"" in %s.", file);
end

function value = textField(settings, name, default)
% settings.(name) as a string, or default when it is missing or empty.
value = default;
if isstruct(settings) && isfield(settings, name) && ~isempty(settings.(name))
    value = string(settings.(name));
end
end

function base = siteUrl(site, projectRoot)
base = site;
if ~contains(base, "://")
    base = replace(string(fullfile(projectRoot, base)), filesep, "/");
    if ~startsWith(base, "/")
        base = "/" + base;
    end
    base = "file://" + base;
end
base = withSlash(base);
end

function url = withSlash(url)
if ~endsWith(url, "/")
    url = url + "/";
end
end

function tf = isServing(base)
% True when the server answers with the build state within half a second.
try
    webread(base + "mat/simulinkDocumentationLinker.json", ...
        weboptions("Timeout", 0.5, "ContentType", "text"));
    tf = true;
catch
    tf = false;
end
end

function out = stablePath(reference)
% The rule of scmd apidoc's output names (_names.docnames).
if reference == "./"
    out = "index";
    return
end
if endsWith(reference, "/")
    parts = split(extractBefore(reference, strlength(reference)), "/")';
    out = strjoin([escapeFolders(parts), "index"], "/");
    return
end
parts = split(reference, "/")';
last = numel(parts);
for i = 1:numel(parts) - 1
    if isBlockContainer(parts(i))
        % A block: its path stays in the file's name.
        parts = [parts(1:i-1), strjoin(parts(i:end), "/")];
        last = i;
        break
    end
end
out = strjoin([escapeFolders(parts(1:last-1)), escapeSegment(parts(last))], "/");
end

function tf = isBlockContainer(name)
tf = any(endsWith(name, [".slx", ".mdl"])) && strlength(name) > 4;
end

function out = escapeFolders(parts)
% A folder's leading _ is escaped too (files keep theirs).
out = strings(size(parts));
for k = 1:numel(parts)
    out(k) = escapeSegment(parts(k));
    if startsWith(out(k), "_")
        out(k) = "~5F" + extractAfter(out(k), 1);
    end
end
end

function out = escapeSegment(segment)
% Keep A-Z a-z 0-9 _ . + @ -; every other byte of the UTF-8 text is ~XX.
safe = ['A':'Z', 'a':'z', '0':'9', '_.+@-'];
bytes = unicode2native(char(segment), "UTF-8");
pieces = strings(1, numel(bytes));
for k = 1:numel(bytes)
    if bytes(k) < 128 && any(char(bytes(k)) == safe)
        pieces(k) = char(bytes(k));
    else
        pieces(k) = sprintf("~%02X", bytes(k));
    end
end
out = strjoin(pieces, "");
devices = ["CON", "PRN", "AUX", "NUL", "COM" + (0:9), "LPT" + (0:9)];
head = split(out, ".");
if ismember(upper(head(1)), devices)
    out = sprintf("~%02X", double(char(extract(out, 1)))) + extractAfter(out, 1);
end
if endsWith(out, ".")
    out = extractBefore(out, strlength(out)) + "~2E";
end
end
