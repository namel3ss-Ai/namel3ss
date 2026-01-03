"use strict";

const fs = require("fs");
const http = require("http");
const https = require("https");
const net = require("net");
const tls = require("tls");
const childProcess = require("child_process");

let patchesInstalled = false;

function installPatches(guards) {
  if (patchesInstalled) {
    return;
  }
  patchesInstalled = true;
  const { guardFilesystem, guardNetwork, guardEnvRead, guardEnvWrite, guardSubprocess } = guards;
  patchFs(fs, guardFilesystem);
  patchFsPromises(fs.promises, guardFilesystem);
  patchHttp(http, "http:", guardNetwork);
  patchHttp(https, "https:", guardNetwork);
  patchConnect(net, guardNetwork);
  patchConnect(tls, guardNetwork);
  patchChildProcess(childProcess, guardSubprocess);
  patchEnv(guardEnvRead, guardEnvWrite);
  patchFetch(guardNetwork);
}

function patchFs(target, guardFilesystem) {
  if (!target) {
    return;
  }
  const readMethods = [
    "readFile",
    "readFileSync",
    "readlink",
    "readlinkSync",
    "readdir",
    "readdirSync",
    "stat",
    "statSync",
    "lstat",
    "lstatSync",
    "access",
    "accessSync",
    "realpath",
    "realpathSync",
  ];
  const writeMethods = [
    "writeFile",
    "writeFileSync",
    "appendFile",
    "appendFileSync",
    "mkdir",
    "mkdirSync",
    "rmdir",
    "rmdirSync",
    "rm",
    "rmSync",
    "unlink",
    "unlinkSync",
    "rename",
    "renameSync",
    "copyFile",
    "copyFileSync",
  ];
  wrapFsMethods(target, readMethods, "r", guardFilesystem);
  wrapFsMethods(target, writeMethods, "w", guardFilesystem);
  wrapFsMethod(target, "createReadStream", "r", guardFilesystem);
  wrapFsMethod(target, "createWriteStream", "w", guardFilesystem);
  wrapFsOpen(target, "open", guardFilesystem);
  wrapFsOpen(target, "openSync", guardFilesystem);
}

function patchFsPromises(target, guardFilesystem) {
  if (!target) {
    return;
  }
  const readMethods = ["readFile", "readlink", "readdir", "stat", "lstat", "access", "realpath"];
  const writeMethods = ["writeFile", "appendFile", "mkdir", "rmdir", "rm", "unlink", "rename", "copyFile"];
  wrapFsMethods(target, readMethods, "r", guardFilesystem);
  wrapFsMethods(target, writeMethods, "w", guardFilesystem);
  wrapFsOpen(target, "open", guardFilesystem);
}

function wrapFsMethods(target, names, mode, guardFilesystem) {
  for (const name of names) {
    wrapFsMethod(target, name, mode, guardFilesystem);
  }
}

function wrapFsMethod(target, name, mode, guardFilesystem) {
  if (!target || typeof target[name] !== "function") {
    return;
  }
  const original = target[name].bind(target);
  target[name] = function (...args) {
    guardFilesystem(args[0], mode);
    return original(...args);
  };
}

function wrapFsOpen(target, name, guardFilesystem) {
  if (!target || typeof target[name] !== "function") {
    return;
  }
  const original = target[name].bind(target);
  target[name] = function (pathValue, flags, ...args) {
    guardFilesystem(pathValue, modeFromFlags(flags));
    return original(pathValue, flags, ...args);
  };
}

function modeFromFlags(flags) {
  if (typeof flags === "string") {
    return isWriteFlagString(flags) ? "w" : "r";
  }
  if (typeof flags === "number") {
    const writeFlags =
      fs.constants.O_WRONLY |
      fs.constants.O_RDWR |
      fs.constants.O_APPEND |
      fs.constants.O_CREAT |
      fs.constants.O_TRUNC;
    return flags & writeFlags ? "w" : "r";
  }
  return "r";
}

function isWriteFlagString(flags) {
  return /[wax+]/.test(String(flags));
}

function patchHttp(moduleRef, protocol, guardNetwork) {
  if (!moduleRef) {
    return;
  }
  if (typeof moduleRef.request === "function") {
    const original = moduleRef.request.bind(moduleRef);
    moduleRef.request = function (...args) {
      const info = requestInfo(args, protocol);
      guardNetwork(info.url, info.method);
      return original(...args);
    };
  }
  if (typeof moduleRef.get === "function") {
    const original = moduleRef.get.bind(moduleRef);
    moduleRef.get = function (...args) {
      const info = requestInfo(args, protocol);
      guardNetwork(info.url, "GET");
      return original(...args);
    };
  }
}

function requestInfo(args, protocol) {
  let url = "";
  let method = "GET";
  let options = null;
  const first = args[0];
  if (typeof first === "string") {
    url = first;
    if (args[1] && typeof args[1] === "object") {
      options = args[1];
    }
  } else if (first && typeof first === "object") {
    if (typeof first.href === "string") {
      url = first.href;
      if (args[1] && typeof args[1] === "object") {
        options = args[1];
      }
    } else {
      options = first;
    }
  }
  if (options && options.method) {
    method = String(options.method).toUpperCase();
  }
  if (!url) {
    url = buildUrlFromOptions(options, protocol);
  }
  return { url, method };
}

function buildUrlFromOptions(options, protocol) {
  if (!options || typeof options !== "object") {
    return `${protocol}//unknown`;
  }
  const proto = options.protocol || protocol;
  const host = options.hostname || options.host || "localhost";
  const port = options.port ? `:${options.port}` : "";
  const pathValue = options.path || "/";
  return `${proto}//${host}${port}${pathValue}`;
}

function patchConnect(moduleRef, guardNetwork) {
  if (!moduleRef || typeof moduleRef.connect !== "function") {
    return;
  }
  const original = moduleRef.connect.bind(moduleRef);
  moduleRef.connect = function (...args) {
    guardNetwork(socketUrlFromArgs(args), "CONNECT");
    return original(...args);
  };
}

function socketUrlFromArgs(args) {
  const first = args[0];
  if (first && typeof first === "object" && !Array.isArray(first)) {
    const host = first.host || first.hostname || "localhost";
    const port = first.port ? `:${first.port}` : "";
    return `socket://${host}${port}`;
  }
  if (typeof first === "number") {
    const host = typeof args[1] === "string" ? args[1] : "localhost";
    return `socket://${host}:${first}`;
  }
  return "socket://unknown";
}

function patchChildProcess(moduleRef, guardSubprocess) {
  if (!moduleRef) {
    return;
  }
  wrapExec(moduleRef, "exec", guardSubprocess);
  wrapExec(moduleRef, "execSync", guardSubprocess);
  wrapSpawn(moduleRef, "spawn", guardSubprocess);
  wrapSpawn(moduleRef, "spawnSync", guardSubprocess);
  wrapExecFile(moduleRef, "execFile", guardSubprocess);
  wrapExecFile(moduleRef, "execFileSync", guardSubprocess);
  wrapFork(moduleRef, "fork", guardSubprocess);
}

function wrapExec(moduleRef, name, guardSubprocess) {
  if (typeof moduleRef[name] !== "function") {
    return;
  }
  const original = moduleRef[name].bind(moduleRef);
  moduleRef[name] = function (command, ...args) {
    guardSubprocess([String(command)]);
    return original(command, ...args);
  };
}

function wrapSpawn(moduleRef, name, guardSubprocess) {
  if (typeof moduleRef[name] !== "function") {
    return;
  }
  const original = moduleRef[name].bind(moduleRef);
  moduleRef[name] = function (command, args, ...rest) {
    const argv = [String(command)];
    if (Array.isArray(args)) {
      argv.push(...args.map((item) => String(item)));
    }
    guardSubprocess(argv);
    return original(command, args, ...rest);
  };
}

function wrapExecFile(moduleRef, name, guardSubprocess) {
  if (typeof moduleRef[name] !== "function") {
    return;
  }
  const original = moduleRef[name].bind(moduleRef);
  moduleRef[name] = function (file, args, ...rest) {
    const argv = [String(file)];
    if (Array.isArray(args)) {
      argv.push(...args.map((item) => String(item)));
    }
    guardSubprocess(argv);
    return original(file, args, ...rest);
  };
}

function wrapFork(moduleRef, name, guardSubprocess) {
  if (typeof moduleRef[name] !== "function") {
    return;
  }
  const original = moduleRef[name].bind(moduleRef);
  moduleRef[name] = function (modulePath, args, ...rest) {
    const argv = [String(modulePath)];
    if (Array.isArray(args)) {
      argv.push(...args.map((item) => String(item)));
    }
    guardSubprocess(argv);
    return original(modulePath, args, ...rest);
  };
}

function patchEnv(guardEnvRead, guardEnvWrite) {
  const raw = process.env;
  const proxy = new Proxy(raw, {
    get(target, prop) {
      if (typeof prop === "string") {
        guardEnvRead(prop);
      }
      return target[prop];
    },
    set(target, prop, value) {
      if (typeof prop === "string") {
        guardEnvWrite(prop);
      }
      target[prop] = value;
      return true;
    },
    deleteProperty(target, prop) {
      if (typeof prop === "string") {
        guardEnvWrite(prop);
      }
      delete target[prop];
      return true;
    },
    ownKeys(target) {
      guardEnvRead("*");
      return Reflect.ownKeys(target);
    },
    has(target, prop) {
      if (typeof prop === "string") {
        guardEnvRead(prop);
      }
      return prop in target;
    },
  });
  process.env = proxy;
}

function patchFetch(guardNetwork) {
  if (typeof globalThis.fetch !== "function") {
    return;
  }
  const original = globalThis.fetch.bind(globalThis);
  globalThis.fetch = function (input, init) {
    const url = input && input.url ? input.url : String(input);
    const method =
      init && init.method
        ? String(init.method).toUpperCase()
        : input && input.method
        ? String(input.method).toUpperCase()
        : "GET";
    guardNetwork(url, method);
    return original(input, init);
  };
}

module.exports = { installPatches };
