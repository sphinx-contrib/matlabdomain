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
%   simulinkDocumentationLinker.json, next to this file, chooses the site;
%   it is read on every call, so switching sites changes no model:
%
%       {"mode": "published",
%        "published": "https://example.org/docs/",
%        "local": "docs/_build/html/"}
%
%   A site without "://" is a folder relative to the folder that holds
%   +sphinxcontrib (the project root), opened as a file:// address.
%
%   The address is the object's stable address (mat/ref/...). It does not
%   know about files whose names differ only by case; their pages get
%   other addresses.
%
%   See also web, sphinxcontrib.matlabdomain.setSimulinkHelp.

arguments
    reference (1,1) string
end
url = baseUrl() + "mat/ref/" + stablePath(reference) + ".html";
end

function base = baseUrl()
folder = fileparts(mfilename("fullpath"));
file = fullfile(folder, "simulinkDocumentationLinker.json");
if ~isfile(file)
    error("sphinxcontrib:matlabdomain:noSettings", ...
        "No settings file %s; sphinx-matlab-quickstart writes it.", file);
end
settings = jsondecode(fileread(file));
mode = string(settings.mode);
if ~ismember(mode, ["published", "local"]) || ~isfield(settings, mode)
    error("sphinxcontrib:matlabdomain:badSettings", ...
        "%s: ""mode"" must be ""published"" or ""local"" and name a field.", file);
end
base = string(settings.(mode));
if ~contains(base, "://")
    projectRoot = fileparts(fileparts(folder));
    base = replace(string(fullfile(projectRoot, base)), filesep, "/");
    if ~startsWith(base, "/")
        base = "/" + base;
    end
    base = "file://" + base;
end
if ~endsWith(base, "/")
    base = base + "/";
end
end

function out = stablePath(reference)
% The rule of sphinx-matlab-apidoc's output names (_names.docnames).
if reference == "./"
    out = "index";
    return
end
if endsWith(reference, "/")
    parts = split(extractBefore(reference, strlength(reference)), "/")';
    out = strjoin([escapeAll(parts), "index"], "/");
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
out = strjoin(escapeAll(parts(1:last)), "/");
end

function tf = isBlockContainer(name)
tf = any(endsWith(name, [".slx", ".mdl", ".xml"])) && strlength(name) > 4;
end

function out = escapeAll(parts)
out = strings(size(parts));
for k = 1:numel(parts)
    out(k) = escapeSegment(parts(k));
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
