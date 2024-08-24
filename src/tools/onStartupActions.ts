import {prisma} from "./prisma";
import bcrypt from "bcrypt";
import {logger} from "./logger";

export class OnStartupActions {
    constructor() {
        logger.debug("OnStartupActions");
    }

    async runAll() {
        logger.debug("OnStartupActions.runAll");
        // await this.createRootIfNotExists();
    }

    // async createRootIfNotExists(): Promise<boolean> {
    //     logger.debug("OnStartupActions.createRootIfNotExists");
    //
    //     // const user = await prisma.user.findUnique({
    //     //     where: {id: 1, username: 'root'}
    //     // });
    //     // if (!user) {
    //     //     const admin: 0 | 1 = 1;
    //     //     const username: string = 'root';
    //     //     const password: string = await bcrypt.hash('root', 10);
    //     //     const name: string = 'Creator';
    //     //     const title: string = 'Creator account'
    //     //     await prisma.user.create({
    //     //         data: {username, password, name, title}
    //     //     });
    //     //     logger.info('Root has been created');
    //     //     return true;
    //     // } else {
    //     //     logger.info('Root already exists');
    //     //     return false;
    //     // }
    // };
}
