function make_docs_sample(outDir)
%MAKE_DOCS_SAMPLE Write the Simulink files of the documentation's sample project.
%   make_docs_sample(outDir) builds the library shapeBlocks and the model
%   shapeAreas, which uses a block of it, and saves them in outDir
%   (docs/src/simulink). Run it in R2024a, so older releases can open the
%   files. Creator and modifier are set to "matlabdomain", so no user name
%   is saved in the files.

arguments
    outDir (1,1) string
end

if ~isfolder(outDir), mkdir(outDir); end
oldDir = cd(outDir);
restoreDir = onCleanup(@() cd(oldDir));
bdclose("all");

lib = "shapeBlocks";
new_system(lib, "Library");
set_param(lib, "Description", "Blocks that compute the areas of shapes.");
addArea(lib + "/Square Area", "Area of a square from its side.", "u(1)^2");
addArea(lib + "/Circle Area", "Area of a circle from its radius.", "pi*u(1)^2");
saveSanitized(lib);
close_system(lib);

mdl = "shapeAreas";
new_system(mdl);
set_param(mdl, "Description", "Computes the area of a square tile.");
add_block("simulink/Sources/In1", mdl + "/side");
set_param(mdl + "/side", "Description", "Side of the tile.", ...
    "OutDataTypeStr", "double", "Unit", "m");
add_block("simulink/Sinks/Out1", mdl + "/area");
set_param(mdl + "/area", "Description", "Area of the tile.", "Unit", "m^2");
load_system(lib);
add_block(lib + "/Square Area", mdl + "/Square Area");
close_system(lib);
add_line(mdl, "side/1", "Square Area/1");
add_line(mdl, "Square Area/1", "area/1");
saveSanitized(mdl);
close_system(mdl, 0);
end

function addArea(path, description, expression)
add_block("simulink/Ports & Subsystems/Subsystem", path);
delete_line(path, "In1/1", "Out1/1");
set_param(path + "/In1", "Name", "u");
set_param(path + "/Out1", "Name", "area");
add_block("simulink/User-Defined Functions/Fcn", path + "/Formula");
set_param(path + "/Formula", "Expr", "scale*" + expression);
add_line(path, "u/1", "Formula/1");
add_line(path, "Formula/1", "area/1");
mask = Simulink.Mask.create(path);
mask.Type = "Shape area";
mask.Description = description;
mask.addParameter("Name", "scale", "Prompt", "Scale factor", "Value", "1", ...
    "Type", "edit");
mask.addParameter("Name", "units", "Prompt", "Units", "Type", "popup", ...
    "TypeOptions", ["SI", "imperial"], "Value", "SI");
end

function saveSanitized(name)
if bdIsLibrary(name), set_param(name, "Lock", "off"); end
set_param(name, "Creator", "matlabdomain", "ModifiedByFormat", "matlabdomain");
save_system(name);
end
