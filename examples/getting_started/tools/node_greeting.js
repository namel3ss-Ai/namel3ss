"use strict";

exports.run = (payload) => {
  const name = payload && payload.name ? payload.name : "there";
  return { message: `Hello ${name}` };
};
