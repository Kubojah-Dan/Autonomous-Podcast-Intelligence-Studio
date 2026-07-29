import axios from "axios";

export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const wsUrl = (path) => {
  const base = BACKEND_URL.replace(/^http/, "ws");
  return `${base}${path}`;
};

export const api = axios.create({ baseURL: API });
