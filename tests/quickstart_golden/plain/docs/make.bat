@ECHO OFF
setlocal

pushd %~dp0

REM Command file for Sphinx documentation
REM Written by sphinx-matlab-quickstart (sphinxcontrib-matlabdomain).

if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=sphinx-build
)
if "%APIDOC%" == "" (
	set APIDOC=scmd apidoc
)
if "%SPHINXAUTOBUILD%" == "" (
	set SPHINXAUTOBUILD=sphinx-autobuild
)
set SOURCEDIR=.
set BUILDDIR=_build
REM The port of make livehtml; the build gives it to Simulink Help links.
if "%LIVEPORT%" == "" (
	set LIVEPORT=8000
)

%SPHINXBUILD% --version >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'sphinx-build' command was not found. Install the documentation
	echo.dependencies, or set the SPHINXBUILD environment variable to the full
	echo.path of 'sphinx-build'.
	echo.
	popd
	exit /b 1
)

if "%1" == "" goto help

if "%1" == "apidoc" (
	%APIDOC% --conf-dir %SOURCEDIR%
	goto end
)

if "%1" == "apidoc-check" (
	%APIDOC% --conf-dir %SOURCEDIR% --check
	goto end
)

if "%1" == "livehtml" (
	%SPHINXAUTOBUILD% %SOURCEDIR% %BUILDDIR%/html -d %BUILDDIR%/doctrees --watch ".." --ignore "*/.venv/*" --ignore "*/.git/*" --pre-build "%APIDOC% --conf-dir . --quiet" --port %LIVEPORT% -D matlab_simulink_server=http://127.0.0.1:%LIVEPORT%/ %SPHINXOPTS% %O%
	goto end
)

REM The API pages are not committed: write them first.
%APIDOC% --conf-dir %SOURCEDIR% --quiet
if errorlevel 1 goto end
%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS% %O%

:end
set EXITCODE=%ERRORLEVEL%
popd
exit /b %EXITCODE%
