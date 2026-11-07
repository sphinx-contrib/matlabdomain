classdef SimulinkHelpTest < matlab.unittest.TestCase
    %SIMULINKHELPTEST Tests of the MATLAB side of the Simulink Help links.
    %   Run in MATLAB R2024a or later from this folder:
    %
    %       results = runtests("SimulinkHelpTest.m")
    %
    %   The fixtures are the R2026b probe files, so run it in R2026b.

    properties
        Root (1,1) string
        Package (1,1) string
    end

    methods (TestMethodSetup)
        function setUp(testCase)
            import matlab.unittest.fixtures.TemporaryFolderFixture
            import matlab.unittest.fixtures.PathFixture
            here = fileparts(mfilename("fullpath"));
            temp = testCase.applyFixture(TemporaryFolderFixture).Folder;
            testCase.Package = fullfile(temp, "tools");
            copyfile(fullfile(here, "..", "..", "sphinxcontrib", "mat_simulink", ...
                "matlab"), testCase.Package);
            testCase.applyFixture(PathFixture(testCase.Package));
            testCase.Root = fullfile(temp, "project");
            mkdir(fullfile(testCase.Root, "src"));
            fixtures = fullfile(here, "fixtures", "R2026b", "slx");
            for name = ["probeLib", "probeModel", "probeRef", "probeSub"]
                copyfile(fullfile(fixtures, name + ".slx"), fullfile(testCase.Root, "src"));
            end
            testCase.writeSettings(struct("mode", "published", ...
                "published", "https://example.org/docs", ...
                "local", "file:///C:/project/docs/_build/html/"));
            testCase.addTeardown(@() bdclose("all"));
        end
    end

    methods (Test)
        function linkerUsesTheSettings(testCase)
            url = sphinxcontrib.matlabdomain.simulinkDocumentationLinker("src/probeLib.slx");
            testCase.verifyEqual(url, "https://example.org/docs/mat/ref/src/probeLib.slx.html");
            testCase.writeSettings(struct("mode", "local", ...
                "local", "file:///C:/project/docs/_build/html/"));
            url = sphinxcontrib.matlabdomain.simulinkDocumentationLinker( ...
                "src/probeLib.slx/Group/Inner Masked");
            testCase.verifyEqual(url, "file:///C:/project/docs/_build/html/" + ...
                "mat/ref/src/probeLib.slx~2FGroup~2FInner~20Masked.html");
            testCase.writeSettings(struct("mode", "local", "local", "docs/_build/html"));
            url = sphinxcontrib.matlabdomain.simulinkDocumentationLinker("src/m.slx");
            expected = "file://" + replace(string(fullfile(testCase.Package, ...
                "docs", "_build", "html")), filesep, "/") + "/mat/ref/src/m.slx.html";
            if ~startsWith(expected, "file:///")
                expected = replace(expected, "file://", "file:///");
            end
            testCase.verifyEqual(url, expected);
        end

        function linkerNeedsValidSettings(testCase)
            testCase.writeSettings(struct("mode", "other"));
            testCase.verifyError(@() sphinxcontrib.matlabdomain.simulinkDocumentationLinker("a.slx"), ...
                "sphinxcontrib:matlabdomain:badSettings");
            delete(testCase.settingsFile());
            testCase.verifyError(@() sphinxcontrib.matlabdomain.simulinkDocumentationLinker("a.slx"), ...
                "sphinxcontrib:matlabdomain:noSettings");
        end

        function libraryBlocksGetHelp(testCase)
            file = fullfile(testCase.Root, "src", "probeLib.slx");
            result = sphinxcontrib.matlabdomain.setSimulinkHelp(file, testCase.Root);
            testCase.verifyEqual(sort(result.Block), sort(["A//B"; "Gain Block"; ...
                "Group/Deeper/Deep Masked"; "Group/Inner Masked"; "Größe"; ...
                "No Description"; "Two" + newline + "Lines"; "v1.2"]));
            kept = result.Block(result.Action == "kept text");
            testCase.verifyEqual(sort(kept), ["Gain Block"; "Group/Inner Masked"]);
            testCase.verifyTrue(all(result.Action(result.Action ~= "kept text") == "set"));

            load_system(file);
            help = get_param("probeLib/Two" + newline + "Lines", "MaskHelp");
            testCase.verifyEqual(string(help), "web(sphinxcontrib.matlabdomain." + ...
                "simulinkDocumentationLinker(""src/probeLib.slx/Two"" + newline + ""Lines""))");
            testCase.verifyEqual(testCase.opens(help), "https://example.org/docs/mat/ref/" + ...
                "src/probeLib.slx~2FTwo~0ALines.html");
            close_system("probeLib", 0);

            again = sphinxcontrib.matlabdomain.setSimulinkHelp(file, testCase.Root);
            testCase.verifyEqual(unique(again.Action(again.Action ~= "kept text")), "unchanged");
            overwritten = sphinxcontrib.matlabdomain.setSimulinkHelp(file, testCase.Root, Overwrite=true);
            testCase.verifyEqual(sort(overwritten.Block(overwritten.Action == "set")), kept);
        end

        function modelsUseTheSystemMask(testCase)
            src = fullfile(testCase.Root, "src");
            model = sphinxcontrib.matlabdomain.setSimulinkHelp( ...
                fullfile(src, "probeModel.slx"), testCase.Root);
            testCase.verifyEqual(model.Action, "kept text");
            model = sphinxcontrib.matlabdomain.setSimulinkHelp( ...
                fullfile(src, "probeModel.slx"), testCase.Root, Overwrite=true);
            testCase.verifyEqual([model.Reference, model.Action], ["src/probeModel.slx", "set"]);
            sub = sphinxcontrib.matlabdomain.setSimulinkHelp( ...
                fullfile(src, "probeSub.slx"), testCase.Root, Overwrite=true);
            testCase.verifyEqual(sub.Action, "set");
            ref = sphinxcontrib.matlabdomain.setSimulinkHelp( ...
                fullfile(src, "probeRef.slx"), testCase.Root);
            testCase.verifyEqual(ref.Action, "no mask");
            ref = sphinxcontrib.matlabdomain.setSimulinkHelp( ...
                fullfile(src, "probeRef.slx"), testCase.Root, CreateSystemMask=true);
            testCase.verifyEqual(ref.Action, "set");
            load_system(fullfile(src, "probeRef.slx"));
            help = Simulink.Mask.get("probeRef").Help;
            testCase.verifyEqual(testCase.opens(help), ...
                "https://example.org/docs/mat/ref/src/probeRef.slx.html");
        end

        function fileMustBeBelowTheRoot(testCase)
            file = fullfile(testCase.Root, "src", "probeModel.slx");
            testCase.verifyError(@() sphinxcontrib.matlabdomain.setSimulinkHelp( ...
                file, testCase.Package), "sphinxcontrib:matlabdomain:outsideRoot");
        end
    end

    methods
        function file = settingsFile(testCase)
            file = fullfile(testCase.Package, "+sphinxcontrib", "+matlabdomain", ...
                "simulinkDocumentationLinker.json");
        end

        function writeSettings(testCase, settings)
            writelines(jsonencode(settings), testCase.settingsFile());
        end
    end

    methods (Static)
        function url = opens(help)
            % The URL that web would get: the argument of web(...).
            inner = extractBetween(string(help), "web(", strlength(help) - 1);
            url = eval(inner);
        end
    end
end
