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
            mkdir(fullfile(testCase.Package, "docs", "_build", "html", "mat"));
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
            testCase.writeSettings(struct("mode", "local", "local", "site/"));
            testCase.verifyError(@() sphinxcontrib.matlabdomain.simulinkDocumentationLinker("a.slx"), ...
                "sphinxcontrib:matlabdomain:noSite");
        end

        function linkerFollowsTheLastBuild(testCase)
            linker = @() sphinxcontrib.matlabdomain.simulinkDocumentationLinker("a.slx");
            % No server answers on this port (the check gives up after 0.5 s).
            testCase.writeSettings(struct("mode", "local", "local", "site/", ...
                "server", "http://127.0.0.1:9/", ...
                "published", "https://example.org/docs/"));
            % Not built: the published site.
            testCase.verifyEqual(linker(), "https://example.org/docs/mat/ref/a.slx.html");
            site = fullfile(testCase.Package, "site");
            mkdir(fullfile(site, "mat"));
            local = "file://" + replace(string(site), filesep, "/");
            if ~startsWith(local, "file:///")
                local = replace(local, "file://", "file:///");
            end
            local = local + "/mat/ref/a.slx.html";
            testCase.verifyEqual(linker(), local);
            % make livehtml: the server, or the local files when it stopped.
            writelines(jsonencode(struct("mode", "server", ...
                "server", "http://127.0.0.1:9/")), ...
                fullfile(site, "mat", "simulinkDocumentationLinker.json"));
            testCase.verifyEqual(linker(), local);
            testCase.applyFixture(matlab.unittest.fixtures.PathFixture( ...
                testCase.fakeServer()));
            testCase.verifyEqual(linker(), "http://127.0.0.1:9/mat/ref/a.slx.html");
            % One person's choice wins over the build.
            testCase.setPreference("published");
            testCase.verifyEqual(linker(), "https://example.org/docs/mat/ref/a.slx.html");
            testCase.setPreference("other");
            testCase.verifyError(linker, "sphinxcontrib:matlabdomain:badSettings");
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

        function folder = fakeServer(testCase)
            % A webread that answers: a server that is running.
            folder = fullfile(testCase.Package, "..", "server");
            mkdir(folder);
            writelines(["function out = webread(varargin)", "out = '{}';", "end"], ...
                fullfile(folder, "webread.m"));
        end

        function setPreference(testCase, mode)
            group = "sphinxcontrib_matlabdomain";
            if ~ispref(group)
                testCase.addTeardown(@() rmpref(group));
            elseif ispref(group, "linkerMode")
                old = getpref(group, "linkerMode");
                testCase.addTeardown(@() setpref(group, "linkerMode", old));
            else
                testCase.addTeardown(@() rmpref(group, "linkerMode"));
            end
            setpref(group, "linkerMode", mode);
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
