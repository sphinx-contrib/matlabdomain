@ECHO OFF

pushd %~dp0

REM Command file for Sphinx documentation
REM The commands run in the project's uv environment, as locked in uv.lock.

if "%UV%" == "" (
	set UV=uv run --frozen --all-extras
)
if "%SPHINXBUILD%" == "" (
	set SPHINXBUILD=%UV% sphinx-build
)
if "%SPHINXAUTOBUILD%" == "" (
	set SPHINXAUTOBUILD=%UV% sphinx-autobuild
)
set SOURCEDIR=.
set BUILDDIR=_build
set SPHINXPROJ=sphinxcontrib-matlabdomain

uv --version >NUL 2>NUL
if errorlevel 9009 (
	echo.
	echo.The 'uv' command was not found: https://docs.astral.sh/uv/
	echo.
	popd
	exit /b 1
)

if "%1" == "" goto help
if "%1" == "livehtml" goto livehtml

%SPHINXBUILD% -M %1 %SOURCEDIR% %BUILDDIR% %SPHINXOPTS%
goto end

:help
%SPHINXBUILD% -M help %SOURCEDIR% %BUILDDIR% %SPHINXOPTS%
goto end

REM Rebuild on every change and serve the HTML at http://127.0.0.1:8000.
REM The pages include files from the worked example, so watch it too.
:livehtml
%SPHINXAUTOBUILD% %SOURCEDIR% %BUILDDIR%\html --watch ..\examples\apidoc %SPHINXOPTS%

:end
set EXITCODE=%ERRORLEVEL%
popd
exit /b %EXITCODE%
