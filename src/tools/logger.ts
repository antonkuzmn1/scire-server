import winston from "winston";

const customFormat1: winston.Logform.Format = winston.format.combine(
    winston.format.colorize(), // Цветовое форматирование
    winston.format.timestamp(),
    winston.format.printf(({ level, message, timestamp }) => {
        return `${timestamp} [${level}]: ${message}`;
    })
);

export const logger: winston.Logger = winston.createLogger({
    level: 'debug',
    // level: 'info',
    format: customFormat1,
    transports: [
        new winston.transports.Console(),
        // new winston.transports.File({ filename: 'combined.log' }),
    ],
});
